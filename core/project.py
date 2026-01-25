import json
import os
from typing import List, Dict, Any
import numpy as np
from core.mask import Mask, MaskType, MediaTransform
from core.media import Media


class ProjectSerializer:
    """Handles saving and loading BadMapper projects to/from .bad files (JSON format)"""

    VERSION = "1.0"

    @staticmethod
    def save_project(file_path: str, masks: List[Mask], projection_width: int, projection_height: int) -> bool:
        """
        Save project to a .bad file in JSON format

        Args:
            file_path: Path to save the .bad file
            masks: List of masks to save
            projection_width: Width of the projection
            projection_height: Height of the projection

        Returns:
            True if successful, False otherwise
        """
        try:
            project_data = {
                "version": ProjectSerializer.VERSION,
                "projection": {
                    "width": projection_width,
                    "height": projection_height
                },
                "masks": []
            }

            for mask in masks:
                mask_data = ProjectSerializer._serialize_mask(mask)
                project_data["masks"].append(mask_data)

            # Ensure .bad extension
            if not file_path.endswith('.bad'):
                file_path += '.bad'

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    @staticmethod
    def load_project(file_path: str) -> Dict[str, Any]:
        """
        Load project from a .bad file

        Args:
            file_path: Path to the .bad file

        Returns:
            Dictionary with 'masks', 'projection_width', and 'projection_height'
            Returns None if loading fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Version check (for future compatibility)
            version = project_data.get("version", "1.0")

            masks = []
            for mask_data in project_data.get("masks", []):
                mask = ProjectSerializer._deserialize_mask(mask_data)
                if mask:
                    masks.append(mask)

            projection = project_data.get("projection", {})

            return {
                "masks": masks,
                "projection_width": projection.get("width", 1920),
                "projection_height": projection.get("height", 1080),
                "version": version
            }
        except Exception as e:
            print(f"Error loading project: {e}")
            return None

    @staticmethod
    def _serialize_mask(mask: Mask) -> Dict[str, Any]:
        """Serialize a single mask to a dictionary"""
        mask_data = {
            "type": mask.mask_type.value,
            "width": int(mask.width),
            "height": int(mask.height),
            "position": [float(mask.position[0]), float(mask.position[1])],
            "vertices": mask.vertices.tolist(),
            "original_vertices": mask.original_vertices.tolist(),
            "rotation": float(mask.rotation),
            "scale": float(mask.scale),
            "media": None,
            "media_transform": {
                "offset_x": float(mask.media_transform.offset_x),
                "offset_y": float(mask.media_transform.offset_y),
                "scale": float(mask.media_transform.scale),
                "rotation": float(mask.media_transform.rotation),
                "perspective_points": mask.media_transform.perspective_points.tolist()
                    if mask.media_transform.perspective_points is not None else None
            }
        }

        # Save media information
        if mask.media:
            mask_data["media"] = {
                "path": mask.media.path,
                "is_video": mask.media.is_video
            }

        return mask_data

    @staticmethod
    def _deserialize_mask(mask_data: Dict[str, Any]) -> Mask:
        """Deserialize a mask from a dictionary"""
        try:
            # Parse mask type
            mask_type_str = mask_data.get("type", "rectangle")
            mask_type = MaskType(mask_type_str)

            # Create mask with basic properties
            width = mask_data.get("width", 400)
            height = mask_data.get("height", 300)
            position = tuple(mask_data.get("position", [100, 100]))

            mask = Mask(mask_type, width, height, position)

            # Restore vertices
            if "vertices" in mask_data:
                mask.vertices = np.array(mask_data["vertices"], dtype=np.float32)

            if "original_vertices" in mask_data:
                mask.original_vertices = np.array(mask_data["original_vertices"], dtype=np.float32)

            # Restore transformations
            mask.rotation = float(mask_data.get("rotation", 0.0))
            mask.scale = float(mask_data.get("scale", 1.0))

            # Restore media transform
            media_transform_data = mask_data.get("media_transform", {})
            mask.media_transform.offset_x = float(media_transform_data.get("offset_x", 0))
            mask.media_transform.offset_y = float(media_transform_data.get("offset_y", 0))
            mask.media_transform.scale = float(media_transform_data.get("scale", 1.0))
            mask.media_transform.rotation = float(media_transform_data.get("rotation", 0.0))

            perspective_points = media_transform_data.get("perspective_points")
            if perspective_points is not None:
                mask.media_transform.perspective_points = np.array(perspective_points, dtype=np.float32)

            # Restore media
            media_data = mask_data.get("media")
            if media_data:
                media_path = media_data.get("path")
                if media_path and os.path.exists(media_path):
                    try:
                        mask.media = Media(media_path)
                    except Exception as e:
                        print(f"Warning: Could not load media from {media_path}: {e}")
                        mask.media = None
                else:
                    print(f"Warning: Media file not found: {media_path}")
                    mask.media = None

            return mask
        except Exception as e:
            print(f"Error deserializing mask: {e}")
            return None
