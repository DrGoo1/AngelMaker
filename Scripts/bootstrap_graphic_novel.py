import unreal
import os

# ---------------------------------------------------
# DEBUG: Confirm which file Unreal is executing
# ---------------------------------------------------
unreal.log(f"[AngelmakerBootstrap] RUNNING FILE: {os.path.abspath(__file__)}")

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
PROJECT_ROOT = "/Game"
LEVEL_FOLDER = f"{PROJECT_ROOT}/Levels/_MASTER"
MASTER_LEVEL_NAME = "Master_Graphic_Novel_Template"

# Lighting / look defaults (Apple Silicon + Lumen baseline)
DIR_LIGHT_LUX = 50000.0
SKY_LIGHT_INTENSITY = 0.3
FOG_DENSITY = 0.01
FOG_HEIGHT_FALLOFF = 0.2

# Exposure (we set it on the CineCamera, which is the most reliable for film)
EXPOSURE_COMPENSATION = 10.0

# Test geometry
CREATE_TEST_GEOMETRY = True


# ---------------------------------------------------
# UTILITIES
# ---------------------------------------------------
def log(msg: str):
    unreal.log(f"[AngelmakerBootstrap] {msg}")


def ensure_folder(path: str):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)
        log(f"Created folder: {path}")
    else:
        log(f"Folder exists: {path}")


def create_or_load_level(level_path: str):
    """
    level_path like /Game/Levels/_MASTER/Master_Graphic_Novel_Template
    UE 5.7-safe: use LevelEditorSubsystem (new_level/load_level).
    """
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    if unreal.EditorAssetLibrary.does_asset_exist(level_path):
        log(f"Loading existing level: {level_path}")
        ok = level_editor.load_level(level_path)
        if not ok:
            raise RuntimeError(f"Failed to load level: {level_path}")
        return

    log(f"Creating new level (blank) at: {level_path}")
    ok = level_editor.new_level(level_path)  # creates + saves + loads
    if not ok:
        raise RuntimeError(f"Failed to create level: {level_path}")

    log("Level created and loaded.")


def spawn(actor_class, location=(0, 0, 0), rotation=(0, 0, 0), label=None):
    loc = unreal.Vector(*location)
    rot = unreal.Rotator(*rotation)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, loc, rot)
    if label:
        actor.set_actor_label(label)
    return actor


def get_all_actors_safe():
    """
    UE 5.7+: avoid deprecated EditorLevelLibrary.get_all_level_actors.
    Uses EditorActorSubsystem.
    """
    try:
        actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        return actor_subsys.get_all_level_actors()
    except Exception:
        # Fallback (should still work, but may warn)
        return unreal.EditorLevelLibrary.get_all_level_actors()


def destroy_actor_safe(actor):
    try:
        actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor_subsys.destroy_actor(actor)
    except Exception:
        unreal.EditorLevelLibrary.destroy_actor(actor)


def set_camera_exposure(cam_actor: unreal.CineCameraActor):
    """
    Set exposure on the camera component post-process settings.
    This is more reliable across UE 5.7 builds than PP Volume struct field names.
    """
    cam = cam_actor.get_cine_camera_component()
    pp = cam.get_editor_property("post_process_settings")

    # Try to force Manual exposure (property name exists in most builds)
    try:
        pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        pp.set_editor_property("b_override_auto_exposure_method", True)
    except Exception:
        pass

    # Try common compensation/bias property names
    set_ok = False
    for bias_name, override_name in [
        ("auto_exposure_bias", "b_override_auto_exposure_bias"),
        ("exposure_compensation", "b_override_exposure_compensation"),
    ]:
        try:
            pp.set_editor_property(bias_name, EXPOSURE_COMPENSATION)
            pp.set_editor_property(override_name, True)
            set_ok = True
            break
        except Exception:
            continue

    cam.set_editor_property("post_process_settings", pp)
    if not set_ok:
        log("WARNING: Could not set exposure compensation on CineCamera post_process_settings (property mismatch).")


def set_ppv_unbound(ppv: unreal.PostProcessVolume) -> bool:
    """
    Make PPV global/unbound. Property name is usually b_unbound.
    """
    try:
        ppv.set_editor_property("b_unbound", True)
        return True
    except Exception:
        return False


def try_set_ppv_exposure_bias(ppv: unreal.PostProcessVolume) -> bool:
    """
    Best-effort. Property names for PostProcessSettings vary across UE versions.
    We try common names; if they fail, camera exposure still ensures sane look.
    """
    try:
        settings = ppv.get_editor_property("settings")
    except Exception:
        return False

    for bias_name, override_name in [
        ("auto_exposure_bias", "b_override_auto_exposure_bias"),
        ("exposure_compensation", "b_override_exposure_compensation"),
    ]:
        try:
            settings.set_editor_property(bias_name, EXPOSURE_COMPENSATION)
            settings.set_editor_property(override_name, True)
            ppv.set_editor_property("settings", settings)
            return True
        except Exception:
            continue

    return False


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def run():
    log("Starting bootstrap...")

    # Create folder structure
    ensure_folder(f"{PROJECT_ROOT}/Levels")
    ensure_folder(LEVEL_FOLDER)
    ensure_folder(f"{PROJECT_ROOT}/Sequences")
    ensure_folder(f"{PROJECT_ROOT}/Characters")
    ensure_folder(f"{PROJECT_ROOT}/Environments")
    ensure_folder(f"{PROJECT_ROOT}/Props")
    ensure_folder(f"{PROJECT_ROOT}/Materials")
    ensure_folder(f"{PROJECT_ROOT}/Audio")
    ensure_folder(f"{PROJECT_ROOT}/Storyboards")
    ensure_folder(f"{PROJECT_ROOT}/ConceptArt")

    level_path = f"{LEVEL_FOLDER}/{MASTER_LEVEL_NAME}"

    # Create/load master level
    create_or_load_level(level_path)

    # Remove existing rig actors + old test geometry (idempotent)
    kill_classes = {
        unreal.DirectionalLight,
        unreal.SkyLight,
        unreal.ExponentialHeightFog,
        unreal.PostProcessVolume,
        unreal.CineCameraActor,
    }
    kill_labels = {"TEST_Plane", "TEST_Cube"}

    for actor in get_all_actors_safe():
        if not actor:
            continue
        try:
            if actor.get_class() in kill_classes or actor.get_actor_label() in kill_labels:
                destroy_actor_safe(actor)
        except Exception:
            # If an actor fails to query, skip it
            continue

    # Spawn lighting rig
    dir_light = spawn(unreal.DirectionalLight, (0, 0, 500), (-50, -35, 0), "Key_DirectionalLight")
    sky_light = spawn(unreal.SkyLight, (0, 0, 500), (0, 0, 0), "Fill_SkyLight")
    fog = spawn(unreal.ExponentialHeightFog, (0, 0, 0), (0, 0, 0), "Atmos_HeightFog")
    ppv = spawn(unreal.PostProcessVolume, (0, 0, 0), (0, 0, 0), "PPV_Global")
    cam = spawn(unreal.CineCameraActor, (-600, 0, 300), (-15, 0, 0), "CAM_Master")

    # Configure Directional Light
    dl_comp = dir_light.get_component_by_class(unreal.DirectionalLightComponent)
    if dl_comp:
        dl_comp.set_editor_property("intensity", DIR_LIGHT_LUX)
        try:
            dl_comp.set_editor_property("shadow_bias", 0.4)
        except Exception:
            pass
        try:
            dl_comp.set_editor_property("contact_shadow_length", 0.2)
        except Exception:
            pass

    # Configure Sky Light
    sl_comp = sky_light.get_component_by_class(unreal.SkyLightComponent)
    if sl_comp:
        sl_comp.set_editor_property("intensity", SKY_LIGHT_INTENSITY)
        try:
            sl_comp.set_editor_property("real_time_capture", True)
        except Exception:
            pass

    # Configure Fog
    fog_comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    if fog_comp:
        fog_comp.set_editor_property("fog_density", FOG_DENSITY)
        fog_comp.set_editor_property("fog_height_falloff", FOG_HEIGHT_FALLOFF)

    # Configure Post Process Volume (best effort)
    if not set_ppv_unbound(ppv):
        log("WARNING: Could not set PPV to Unbound (b_unbound property not found). You can set it manually in Details.")
    if not try_set_ppv_exposure_bias(ppv):
        log("NOTE: Could not set exposure bias on PPV (property mismatch). Using camera exposure instead.")

    # Configure Camera exposure (reliable film control)
    set_camera_exposure(cam)

    # Create test geometry
    if CREATE_TEST_GEOMETRY:
        plane = spawn(unreal.StaticMeshActor, (0, 0, 0), (0, 0, 0), "TEST_Plane")
        cube = spawn(unreal.StaticMeshActor, (0, 0, 100), (0, 0, 0), "TEST_Cube")

        plane_mesh = unreal.load_asset("/Engine/BasicShapes/Plane.Plane")
        cube_mesh = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")

        plane_comp = plane.get_component_by_class(unreal.StaticMeshComponent)
        cube_comp = cube.get_component_by_class(unreal.StaticMeshComponent)

        if plane_comp and plane_mesh:
            plane_comp.set_static_mesh(plane_mesh)
            plane.set_actor_scale3d(unreal.Vector(20, 20, 1))

        if cube_comp and cube_mesh:
            cube_comp.set_static_mesh(cube_mesh)
            cube.set_actor_scale3d(unreal.Vector(2, 2, 4))

    # Save current level (UE 5.7-safe)
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    level_editor.save_current_level()

    log("Bootstrap complete.")
    log(f"Master level ready: {level_path}")
    log("Next: Duplicate the master level per song and build sequences under /Game/Sequences.")


if __name__ == "__main__":
    run()