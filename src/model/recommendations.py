# Scoring reference for menu items
#
# --- Allergens ---
# >= 0.8, Guarantees the presence, -999
# >= 0.5, May have the presence, -20 per allergen
# default, Little to no presence, 0
#
# --- Diets ---
# any <= 0.4, Not suitable, -999
# any <= 0.8, May not be suitable, -20 per diet
# default, Suitable, 0
#
# --- Cuisine ---
# Word contains in menuitem.cuisine, +5
#
# --- Dislikes ---
# Word in disliked ingredients (UserPreferences) contains in menuitem ingredients, -8
# (can't do above yet)
# Is in disliked dishes, -10
#
# --- Likes ---
# Below is to use encoding?
# Word in liked menu (UserPreferences) contains in menuitem.name, +15
# The stall is liked, +10  (can't do yet)
#
# --- Saves ---
# The menu is saved, +5     # We want to see other menus too
# The stall is saved, +10   # Let us see more menu of stall  (can't do yet)
import os
import logging

import pandas as pd
from pathlib import Path
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier, Literal
from random import choice
from uuid import UUID
import json

from .data_utils import extract_uuids, dict_from

db = os.getenv("DATABASE_URL")

debug = os.getenv("DEBUG")

logger = logging.getLogger("recommendations")
logdir = Path(os.getcwd()).joinpath("logs")

if not logdir.exists():
    logdir.mkdir(parents=True)

logfile = logging.FileHandler(
    filename=logdir.joinpath("recommendations.log"), encoding="utf-8"
)

if debug:
    logger.setLevel(logging.DEBUG)
    logfile.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
    logfile.setLevel(logging.INFO)

logger.addHandler(logfile)


class AsyncConnectionPoolSingleton:
    __instance = None

    __pool: AsyncConnectionPool

    def __init__(self):
        raise RuntimeError("Call get() instead")

    @classmethod
    def get(cls, conninfo: str, **kwargs) -> AsyncConnectionPool:
        if not cls.__instance:
            cls.__instance = cls.__new__(cls)
            cls.__instance.__pool = AsyncConnectionPool(conninfo, **kwargs)
        return cls.__instance.__pool


def get_db_connection_pool():
    if db:
        try:
            return AsyncConnectionPoolSingleton.get(db, open=True)
        except Exception as e:
            raise RuntimeError(f"Cannot connect to database: {e}")
    else:
        logger.error("DATABASE_URL is not specified in environment")
    raise RuntimeError("Cannot connect to database")

rootdir = Path(os.getcwd())
common_words: dict[str, list[float]] = {}
with open(rootdir.joinpath('generated/tensors/common_words.json'), mode="r") as f:
    common_words = json.load(f)

def common_word_normalize(score: float):
    return min(score * (15 / 0.9), 15)

async def generate_recommendations_for_user(user_id: str):
    try:
        pool = get_db_connection_pool()
        if not pool:
            return
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.debug(f"Skipping recommendations generation for {user_id}")
        return

    try:
        async with pool.connection() as conn:
            # Prelimanary checks
            # Is user exists,
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT count(*) FROM kueater.userprofile WHERE id = '{user_id}'"
                )
                count = await cur.fetchone()
                if not count or not count[0]:
                    # User does not exist
                    logger.debug(f"User {user_id} does not exist")
                    return
            # If user has preferences, (edge case)
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT count(*) FROM kueater.user_profile_preferences WHERE user_id = '{user_id}'"
                )
                count = await cur.fetchone()
                if not count or not count[0]:
                    # Preference not exist
                    logger.debug(f"User {user_id} does not have preferences set")
                    return
            
            logger.info(f"Start generating recommendations for {user_id}")

            # Preliminary checks passed, begin transaction
            async with conn.cursor(row_factory=dict_row) as cur:
                async with conn.transaction():
                    # Stale all recommendations
                    _s = f"SELECT kueater.stale_menuitem_scores_of('{user_id}');"
                    await cur.execute(_s)

                    # Reset user tally count
                    # _s = f"SELECT kueater.reset_tally('{user_id}');"
                    # await cur.execute(_s)

                    # Retrieve user preferences
                    _s = SQL(
                        "SELECT json_agg(json_build_object({fields})) AS preferences "
                        "FROM {table} u LEFT JOIN {join} upp ON u.id = upp.user_id "
                        "LEFT JOIN {next_join} up ON upp.preferences_id = up.id "
                        "WHERE u.id = {uid};"
                    ).format(
                        fields=SQL(
                            "'diets', up.diets, 'allergies', up.allergies, "
                            "'cuisines', up.cuisines, 'disliked_ingredients', up.disliked_ingredients, "
                            "'favorite_dishes', up.favorite_dishes"
                        ),
                        table=Identifier("kueater", "userprofile"),
                        join=Identifier("kueater", "user_profile_preferences"),
                        next_join=Identifier("kueater", "user_preferences"),
                        uid=f"{user_id}",
                    )

                    logger.debug(_s.as_string())

                    res = await cur.execute(_s)
                    preference_obj = await res.fetchone()

                    # Gets the first object
                    preference_obj: dict[str, list[str] | None] = preference_obj[
                        "preferences"
                    ][0]
                    preference_obj = {
                        k: (v if v else []) for k, v in preference_obj.items()
                    }

                    # This means we successfully get preferences
                    logger.debug(preference_obj)

                    # Retrieve likes, dislikes, saved
                    # SELECT json_agg(likes) AS likes FROM (SELECT user_id, json_agg(menu_id)
                    # AS likes FROM liked_item GROUP BY user_id) s;
                    _s = SQL(
                        "SELECT json_agg({alias}) AS {alias} "
                        "FROM (SELECT user_id, json_agg({fields}) AS {alias} FROM {table} GROUP BY user_id) t "
                        f"WHERE user_id = '{user_id}'"
                    )

                    liked_menu_sql = _s.format(
                        fields=SQL("menu_id"),
                        alias=SQL("likes"),
                        table=Identifier("kueater", "liked_item"),
                    )

                    disliked_menu_sql = _s.format(
                        fields=SQL("menu_id"),
                        alias=SQL("dislikes"),
                        table=Identifier("kueater", "disliked_item"),
                    )

                    saved_menu_sql = _s.format(
                        fields=SQL("menu_id"),
                        alias=SQL("saves"),
                        table=Identifier("kueater", "saved_item"),
                    )

                    liked_stall_sql = _s.format(
                        fields=SQL("stall_id"),
                        alias=SQL("likes"),
                        table=Identifier("kueater", "liked_stall"),
                    )

                    saved_stall_sql = _s.format(
                        fields=SQL("stall_id"),
                        alias=SQL("saves"),
                        table=Identifier("kueater", "saved_stall"),
                    )

                    # Retreive menu and stalls
                    # Don't mind my blursed code
                    liked_menus: list[str] = (
                        await (await cur.execute(liked_menu_sql)).fetchone()
                    )["likes"]
                    disliked_menus: list[str] = (
                        await (await cur.execute(disliked_menu_sql)).fetchone()
                    )["dislikes"]
                    saved_menus: list[str] = (
                        await (await cur.execute(saved_menu_sql)).fetchone()
                    )["saves"]
                    liked_stalls: list[str] = (
                        await (await cur.execute(liked_stall_sql)).fetchone()
                    )["likes"]
                    saved_stalls: list[str] = (
                        await (await cur.execute(saved_stall_sql)).fetchone()
                    )["saves"]

                    liked_menus = liked_menus[0] if liked_menus else []
                    disliked_menus = disliked_menus[0] if disliked_menus else []
                    saved_menus = saved_menus[0] if saved_menus else []
                    liked_stalls = liked_stalls[0] if liked_stalls else []
                    saved_stalls = saved_stalls[0] if saved_stalls else []

                    logger.debug(liked_menus)
                    logger.debug(disliked_menus)
                    logger.debug(saved_menus)
                    logger.debug(liked_stalls)
                    logger.debug(saved_stalls)

                    # Get the entire menu item database
                    menu_db_sql = "SELECT * FROM kueater.get_all_menuitems_with_ingredients();"
                    res = await (await cur.execute(menu_db_sql)).fetchall()
                    df = pd.DataFrame([r.copy() for r in res])
                    
                    _df = df['ingredients'].apply(lambda x: extract_uuids(str(x)))
                    _df = _df.reset_index()
                    _df['menu_id'] = df['menu_id']
                    _df.drop('index', axis=1, inplace=True)

                    # Construct standard Python dictionary
                    # MenuItem id: List of Ingredient id
                    menu_item_ingredients_dict: dict[UUID, list] = {}
                    for _, pair in _df.explode('ingredients').fillna("").iterrows():
                        if pair["menu_id"] not in menu_item_ingredients_dict.keys():
                            menu_item_ingredients_dict[pair["menu_id"]] = []
                        if pair["ingredients"]:
                            menu_item_ingredients_dict[pair["menu_id"]].append(pair["ingredients"])

                    user_concern_diets = preference_obj['diets']
                    user_concern_allergies = preference_obj['allergies']

                    menus = list(menu_item_ingredients_dict.keys())

                    # Inserting each recommendation object!

                    for menu in menus:

                        logger.debug(menu)

                        final_score = 0

                        warn_reasons: list[str] = []
                        good_reasons: list[str] = []

                        ingredients = menu_item_ingredients_dict[menu]

                        logger.debug(ingredients)

                        diet_scores = []
                        allergens_scores = []

                        for ingredient in ingredients:
                            _s = f"SELECT kueater.get_ingredient_compatibility_score('{ingredient}');"
                            res = await (await cur.execute(_s)).fetchone()
                            item_diets = dict_from(res["get_ingredient_compatibility_score"][2])
                            item_allergens = dict_from(res["get_ingredient_compatibility_score"][3])

                            logger.debug(item_diets)
                            logger.debug(item_allergens)

                            diet_scores.append(item_diets)
                            allergens_scores.append(item_allergens)

                        # Check diet
                        # Does user have any concerning diets?
                        if user_concern_diets:

                            # What diet?
                            diet_reasoning = {
                                "incompatible": set(),
                                "maybe": set()
                            }

                            curr_score = 1.0

                            # Check for each diet
                            for diet in user_concern_diets:
                                for scoreset in diet_scores:
                                    s = scoreset[diet]
                                    if s <= 0.4:
                                        diet_reasoning["incompatible"].add(diet)
                                    elif s <= 0.7:
                                        diet_reasoning["maybe"].add(diet)
                                    if s < curr_score:
                                        curr_score = s
                            
                            if diet_reasoning["incompatible"]:
                                warn_reasons.append(
                                    f"Not compatible with your diet: {', '.join(diet_reasoning['incompatible'])}"
                                )
                            elif diet_reasoning["maybe"]:
                                warn_reasons.append(
                                    f"Maybe compatible with your diet: {', '.join(diet_reasoning['maybe'])}"
                                )

                            if curr_score <= 0.4:
                                final_score = -999  # Set to -999
                            elif curr_score <= 0.8:
                                final_score -= (20 * len(diet_reasoning["maybe"]))
                            
                        # Check allergens
                        # Does user have any allergies concerned?
                        if user_concern_allergies:

                            # What allergen?
                            allergen_reasoning = {
                                "contains": set(),
                                "unsure": set()
                            }

                            curr_score = 0.0

                            # Check for each allergen
                            for allergen in user_concern_allergies:
                                for scoreset in allergens_scores:
                                    s = scoreset[allergen]
                                    if s >= 0.7:
                                        allergen_reasoning["contains"].add(allergen)
                                    elif s >= 0.5:
                                        allergen_reasoning["unsure"].add(allergen)
                                    if s > curr_score:
                                        curr_score = s
                            
                            if allergen_reasoning["contains"]:
                                warn_reasons.append(
                                    f"Contains allergen: {', '.join(allergen_reasoning['contains'])}"
                                )
                            elif allergen_reasoning["unsure"]:
                                warn_reasons.append(
                                    f"May contain traces of: {', '.join(allergen_reasoning['unsure'])}"
                                )

                            if curr_score >= 0.7:
                                final_score = -999  # Set to -999
                            elif curr_score >= 0.5:
                                final_score -= (20 * len(allergen_reasoning["unsure"]))

                        # Check disliked
                        if str(menu) in disliked_menus:
                            logger.debug(f"{menu} is disliked!")
                            final_score -= 10
                        
                        # Check liked

                        # Use pgsql to get distance of menu to keyword.
                        if common_words:
                            scores = {}
                            for word in preference_obj['favorite_dishes']:
                                if word in common_words.keys():
                                    vectors = common_words[word]
                                    _s = SQL(
                                        "SELECT 1 - ({embedding} <=> embedding) AS distance "\
                                        "FROM {table} WHERE object_type = 'menuitem' AND "\
                                        f"object_id = '{menu}'"
                                    ).format(
                                        embedding=Literal(str(vectors)),
                                        table=Identifier("kueater", "embeddings")
                                    )

                                    res = await (await cur.execute(_s)).fetchone()
                                    score = common_word_normalize(res["distance"])
                                    scores[word] = score
                            if scores:
                                final_score += sum(scores.values())
                                if min(scores.values()) >= 8:
                                    good_reasons.append(f"Because you like {choice([
                                        k for k, s in scores.items() if s >= 8
                                    ])}")


                        if str(menu) in liked_menus:
                            logger.debug(f"{menu} is liked!")
                            final_score += 10
                        
                        # Check saved
                        if str(menu) in saved_menus:
                            logger.debug(f"{menu} is saved!")
                            final_score += 5

                        reasons = lambda: good_reasons if final_score >= 10 else warn_reasons
                        reasons_str = lambda: r"\n".join(reasons()) if reasons() else ""
                        
                        _s = SQL(
                            "INSERT INTO {table} (user_id, menu_id, score, reasoning) VALUES "\
                            f"('{user_id}', '{menu}', {final_score}, '{reasons_str()}');"
                        ).format(
                            table=Identifier("kueater", "menuitem_scores")
                        )

                        await cur.execute(_s)
    
            # Insertions finished
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT kueater.refresh_menuitem_scores();"
                )

            logger.info(f"Completed recommendations generation for: {user_id}")

    except Exception as e:
        logger.exception(e)
        return
