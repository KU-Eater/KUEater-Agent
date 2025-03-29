# Takes two CSVs, menuitem and stall to provide an SQL script that adds new entries to respective tables.
import os
import sys
from typing import Callable, Tuple
import pandas as pd
from pathlib import Path
from uuid_extensions import uuid7str

root_dir = Path(os.path.abspath(__file__)).parents[1]
sys.path.append(str(root_dir))

from src.model.encoder import encode_sync


def show_help():
    print("Usage: database_populate_sql.py [data_version]")
    print(
        "The script finds two files in, data/menuitems-[data_version].csv and\n"
        "data/stalls-[data_version].csv and generates a single SQL file to add all\n"
        "data entries into a SQL database."
    )


def new_transaction(fn: Callable[..., Tuple[str, pd.DataFrame]]):
    def wrapper(*dfs):
        text, dataframe = fn(*dfs)
        return (
            f"""BEGIN TRANSACTION;
    
    {text}
    
    COMMIT;""",
            dataframe,
        )

    return wrapper


@new_transaction
def generate_ingredient_sql(menuitem_df: pd.DataFrame) -> Tuple[str, pd.DataFrame]:
    
    print("== GENERATING INGREDIENT SECTION... ==")
    
    _header = """/*
    INGREDIENTS SECTION -- ENTRIES, EMBEDDINGS
    */
    """

    df = menuitem_df.iloc[:, 9:11]  # Main and Hidden Ingredients
    df = df.map(lambda x: [item.strip() for item in x.split(",")])
    iset = set(df.iloc[:, 0].explode().to_list() + df.iloc[:, 1].explode().to_list())
    iset.remove("")

    ing_uid_df = pd.DataFrame(iset, columns=["name"])
    ing_uid_df["uuid"] = ing_uid_df.apply(lambda x: uuid7str(), axis=1)
    
    print("== INSERT ENTRIES ==")

    statement = """INSERT INTO kueater.ingredient (id, name) VALUES"""
    statement += "\n".join(
        [
            f"('{row['uuid']}', '{row['name']}');"
            if int(idx) >= len(ing_uid_df) - 1
            else f"('{row['uuid']}', '{row['name']}'),"
            for idx, row in ing_uid_df.iterrows()
        ]
    )

    statement += "\n"
    
    print("== INSERT EMBEDDINGS ==")

    ing_emb_df = ing_uid_df.copy()
    ing_emb_df["embedding"] = ing_emb_df.apply(lambda x: encode_sync(x["name"]), axis=1)

    statement += """INSERT INTO kueater.embeddings (object_id, object_type, string, lang, embedding) VALUES"""
    statement += "\n".join(
        [
            f"('{row['uuid']}', 'ingredient', '{row['name']}', 'en', '{row['embedding']}');"
            if int(idx) >= len(ing_emb_df) - 1
            else f"('{row['uuid']}', 'ingredient', '{row['name']}', 'en', '{row['embedding']}'),"
            for idx, row in ing_emb_df.iterrows()
        ]
    )

    return _header + statement, ing_uid_df


@new_transaction
def generate_menuitem_sql(
    menuitem_df: pd.DataFrame, ingredient_uids: pd.DataFrame
) -> Tuple[str, pd.DataFrame]:
    
    print("== GENERATING MENUITEM SECTION... ==")
    
    _header = """/*
    MENUITEM SECTION -- ENTRIES, EMBEDDINGS, RELATIONSHIPS
    */
    """

    df = pd.DataFrame(menuitem_df.iloc[:, [1, 3, 4, 5, 7, 9, 10, 11]])

    df.columns = [
        "lock",
        "name",
        "price",
        "cuisine",
        "type",
        "main_ingredients",
        "hidden_ingredients",
        "image",
    ]
    df["uuid"] = df.apply(lambda x: uuid7str(), axis=1)
    
    print("== INSERT ENTRIES ==")

    statement = """INSERT INTO kueater.menuitem (id, name, price, image, cuisine, food_type) VALUES"""
    statement += "\n".join(
        [
            f"('{row['uuid']}', '{row['name']}', {row['price']},"
            f"'{row['image'] if row['image'] else ''}',"
            f"'{row['cuisine'] if row['cuisine'] else ''}',"
            f"'{row['type'] if row['type'] else ''}');"
            if int(idx) >= len(df) - 1
            else f"('{row['uuid']}', '{row['name']}', {row['price']},"
            f"'{row['image'] if row['image'] else ''}',"
            f"'{row['cuisine'] if row['cuisine'] else ''}',"
            f"'{row['type'] if row['type'] else ''}'),"
            for idx, row in df.iterrows()
        ]
    )
    
    print("== INSERT EMBEDDINGS ==")
    
    menu_emb_df = df.loc[:, ["name", "uuid"]]
    menu_emb_df["embedding"] = menu_emb_df.apply(lambda x: encode_sync(x["name"]), axis=1)
    
    statement += "\n"
    statement += "INSERT INTO kueater.embeddings (object_id, object_type, string, lang, embedding) VALUES"
    statement += "\n".join(
        [
            f"('{row['uuid']}', 'menuitem', '{row['name']}', 'en', '{row['embedding']}');"
            if int(idx) >= len(menu_emb_df) - 1
            else f"('{row['uuid']}', 'menuitem', '{row['name']}', 'en', '{row['embedding']}'),"
            for idx, row in menu_emb_df.iterrows()
        ]
    )
    
    print("== INSERT RELATIONSHIPS ==")
    
    ingredient_uids_indexed = ingredient_uids.set_index("name")
    statement += "\n"
    statement += "INSERT INTO kueater.menu_ingredient (menu_id, ingredient_id) VALUES"
    
    for idx, row in df.iterrows():
        
        uid = row["uuid"]
        ingredients = [
            i.strip() for i in row["main_ingredients"].split(",")
        ] + [
            i.strip() for i in row["hidden_ingredients"].split(",")
        ]
        
        statement += menuitem_ingredient_relationships(
            uid,
            ingredients,
            ingredient_uids_indexed,
            int(idx) >= len(df) - 1
        )
        
        statement += "\n"

    return _header + statement, df.loc[:, ["lock", "name", "uuid"]]


def menuitem_ingredient_relationships(uid, ingredients, ingredient_uids, final=False) -> str:
    sqls = []
    for idx, i in enumerate(ingredients):
        if not i:
            continue
        ingredient_uid = ingredient_uids.loc[i, 'uuid']
        if final and idx >= len(ingredients) - 1:
            sqls.append(f"('{uid}', '{ingredient_uid}');")
        else:
            sqls.append(f"('{uid}', '{ingredient_uid}'),")
    
    return "\n".join(sqls)


@new_transaction
def generate_stall_sql(
    stall_df: pd.DataFrame, menu_uids: pd.DataFrame
) -> Tuple[str, pd.DataFrame]:
    
    print("== GENERATING STALL SECTION... ==")

    _header = """/*
    STALL SECTION -- ENTRIES, RELATIONSHIPS
    */
    """
    
    def __double_single_quotes(text):
        return text.replace("'", "''")
    
    df = pd.DataFrame(stall_df.iloc[:, [3, 5, 7, 9, 11, 12]])
    df.columns = [
        "lock",
        "name",
        "image",
        "tags",
        "open",
        "close"
    ]
    df["uuid"] = df.apply(lambda x: uuid7str(), axis=1)
    df["name"] = df["name"].map(__double_single_quotes)

    print("== INSERT ENTRIES ==")

    statement = """INSERT INTO kueater.stall (id, name, lock, image, open_hour, close_hour, tags) VALUES"""
    statement += "\n".join(
        [
            f"('{row["uuid"]}', '{row['name']}', {int(row['lock'])},"
            f"'{row['image'] if row['image'] else ''}',"
            f"'{row['open'] if row['open'] else ''}',"
            f"'{row['close'] if row['close'] else ''}',"
            f"'{row['tags'] if row['tags'] else ''}');"
            if int(idx) >= len(df) - 1
            else f"('{row["uuid"]}', '{row['name']}', {int(row['lock'])},"
            f"'{row['image'] if row['image'] else ''}',"
            f"'{row['open'] if row['open'] else ''}',"
            f"'{row['close'] if row['close'] else ''}',"
            f"'{row['tags'] if row['tags'] else ''}'),"
            for idx, row in df.iterrows()
        ]
    )
    
    print("== INSERT RELATIONSHIPS ==")
    
    statement += "\n"
    statement += "INSERT INTO kueater.stall_menu (stall_id, menu_id) VALUES"
    
    relationships = []
    
    for idx, row in df.iterrows():
        uid = row["uuid"]
        lock = int(row["lock"])
        
        filtered_menus = menu_uids.loc[menu_uids["lock"] == lock]
    
        for mid, (_, menu) in enumerate(filtered_menus.iterrows()):
            
            if int(mid) >= len(filtered_menus) - 1 and int(idx) >= len(df) - 1:
                relationships.append(f"('{uid}', '{menu["uuid"]}');")
            else:
                relationships.append(f"('{uid}', '{menu["uuid"]}'),")
        
    statement += "\n".join(relationships)
    
    return _header + statement, df


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        show_help()
        sys.exit(1)

    data_version = args[0]

    data_dir = root_dir.joinpath("data")

    menuitem_file = data_dir.joinpath(f"menuitems-{data_version}.csv")
    stall_file = data_dir.joinpath(f"stalls-{data_version}.csv")

    if not any([menuitem_file.exists(), stall_file.exists()]):
        print(f"Missing data file(s) for: {data_version}")
        sys.exit(1)

    generated_dir = root_dir.joinpath("generated/sql")
    if not generated_dir.exists():
        generated_dir.mkdir(parents=True)

    _header = f"""/*
    KU Eater Database Population Script v{data_version}
    */
    """

    menuitem_df = pd.read_csv(menuitem_file, encoding="utf-8", na_values=["–"]).fillna(
        ""
    )
    stall_df = pd.read_csv(stall_file, encoding="utf-8").fillna("")

    (ingredient_sql, ingredient_uid_df) = generate_ingredient_sql(menuitem_df)
    (menuitem_sql, menuitem_uid_df) = generate_menuitem_sql(
        menuitem_df, ingredient_uid_df
    )
    (stall_sql, _) = generate_stall_sql(stall_df, menuitem_uid_df)

    print("== FINISHING UP ==")

    parts = [_header, ingredient_sql, menuitem_sql, stall_sql]

    with open(
        generated_dir.joinpath(f"populate_{data_version}.sql"),
        mode="w", encoding="utf-8"
        ) as f:
        f.write("\n".join(parts))
