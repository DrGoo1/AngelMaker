import json
import unreal

"""
AngelMaker EP01 Scene Builder (Scaffold)
- Reads shots_ep01.json
- Creates/updates Level Sequences (later)
- Spawns cameras (later)
- Applies lens + movement templates (later)
- Applies selective-color stencil ID per sequence (later)
"""

DATA_ASSET = "/Game/Tools/Data/shots_ep01"  # if later we convert JSON to a UE DataAsset

def load_json(path_on_disk: str) -> dict:
    with open(path_on_disk, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    # Adjust path as needed for your machine; we keep JSON in Content so it's in repo
    json_path = unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_content_dir() + "Tools/Data/shots_ep01.json"
    )
    data = load_json(json_path)
    unreal.log(f"[AngelMaker] Loaded EP01 shot plan: {data.get('episode')}")
    for seq in data.get("sequences", []):
        unreal.log(f" - Sequence: {seq.get('name')} (stencilActiveId={seq.get('stencilActiveId')}) shots={len(seq.get('shots', []))}")

if __name__ == "__main__":
    main()
