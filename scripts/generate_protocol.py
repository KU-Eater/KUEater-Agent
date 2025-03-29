from pathlib import Path
from grpc_tools import protoc
import sys
import os


def main():
    root_dir = Path(os.path.abspath(__file__)).parents[1]

    protocol_dir = root_dir.joinpath("protocol")
    protocol_whitelist = ["agent"]

    if not protocol_dir.exists():
        print(f"{protocol_dir} does not exist")
        sys.exit(1)

    def __list_all_protobuf(root: Path, subdirs: list[str] = []):
        root_dir = root.resolve()

        _sub = []
        if subdirs:
            _sub = {root_dir / Path(p) for p in subdirs}
        else:
            return [str(p) for p in root_dir.rglob("*.proto")]

        matched = []
        for path in root_dir.rglob("*.proto"):
            if any(path.parent == p or path.parent.is_relative_to(p) for p in _sub):
                matched.append(str(path))

        return matched

    protocol_files = __list_all_protobuf(protocol_dir, protocol_whitelist)

    if not protocol_files:
        print("No protocol buffer definitions found, exiting...")
        sys.exit()

    generated_dir = root_dir.joinpath("src/generated")
    if not generated_dir.exists():
        generated_dir.mkdir()

    # --- From grpc_tools/protoc.py

    proto_include = protoc._get_resource_file_name("grpc_tools", "_proto")
    sys.exit(
        protoc.main(
            [
                "-I{}".format(proto_include),
                "-I{}".format(protocol_dir),
                *(
                    "--{}_out={}".format(opt, generated_dir)
                    for opt in ("python", "pyi", "grpc_python")
                ),
                *(p for p in protocol_files),
            ]
        )
    )


if __name__ == "__main__":
    main()
