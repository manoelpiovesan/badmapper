import cv2
import numpy as np

class Renderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.output_canvas = None
        self.reset_canvas()

    def reset_canvas(self):
        self.output_canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def render_mask(self, mask):
        if mask.media is None:
            return

        frame = mask.media.get_current_frame()
        if frame is None:
            return

        media_h, media_w = frame.shape[:2]
        transform = mask.media_transform

        # Create transformed media canvas
        transformed_media = frame.copy()

        # Apply rotation
        if transform.rotation != 0:
            center = (media_w / 2, media_h / 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, transform.rotation, 1.0)
            transformed_media = cv2.warpAffine(transformed_media, rotation_matrix, (media_w, media_h))

        # Apply scale
        if transform.scale != 1.0:
            new_w = int(media_w * transform.scale)
            new_h = int(media_h * transform.scale)
            transformed_media = cv2.resize(transformed_media, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            # Adjust to keep centered
            if new_w < media_w or new_h < media_h:
                # Pad
                pad_w = max(0, (media_w - new_w) // 2)
                pad_h = max(0, (media_h - new_h) // 2)
                transformed_media = cv2.copyMakeBorder(transformed_media, pad_h, media_h - new_h - pad_h,
                                                       pad_w, media_w - new_w - pad_w,
                                                       cv2.BORDER_CONSTANT, value=(0, 0, 0))
            else:
                # Crop
                crop_w = (new_w - media_w) // 2
                crop_h = (new_h - media_h) // 2
                transformed_media = transformed_media[crop_h:crop_h + media_h, crop_w:crop_w + media_w]

        # Apply offset by translating the source points
        media_points = np.array([
            [0, 0],
            [media_w, 0],
            [media_w, media_h],
            [0, media_h]
        ], dtype=np.float32)

        # Offset the media within the mask space
        offset_scale = 0.5  # Scale offset relative to mask size
        media_points[:, 0] -= transform.offset_x * offset_scale
        media_points[:, 1] -= transform.offset_y * offset_scale

        # Perspective transform from media to mask vertices
        if len(mask.vertices) >= 4:
            dest_points = mask.vertices[:4].astype(np.float32)
        else:
            # For triangles, add a fourth point
            dest_points = np.vstack([mask.vertices, mask.vertices[0]]).astype(np.float32)

        # Get homography
        try:
            H = cv2.getPerspectiveTransform(media_points, dest_points)
            warped = cv2.warpPerspective(transformed_media, H, (self.width, self.height),
                                        flags=cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_CONSTANT,
                                        borderValue=(0, 0, 0))

            # Create mask for blending
            mask_img = np.zeros((self.height, self.width), dtype=np.uint8)
            cv2.fillPoly(mask_img, [dest_points.astype(np.int32)], 255)

            # Blend with output canvas
            mask_3ch = cv2.cvtColor(mask_img, cv2.COLOR_GRAY2BGR)
            self.output_canvas = np.where(mask_3ch > 0, warped, self.output_canvas)
        except:
            pass

    def get_output(self):
        return self.output_canvas
