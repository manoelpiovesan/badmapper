import cv2
import numpy as np

class Renderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.output_canvas = None
        self.show_grid = False
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
        try:
            if len(mask.vertices) == 3:
                # For triangles, use affine transform with 3 points
                # Map media triangle to mask triangle
                media_triangle = np.array([
                    [0, 0],
                    [media_w, 0],
                    [media_w / 2, media_h]
                ], dtype=np.float32)

                # Apply offset to source triangle
                media_triangle[:, 0] -= transform.offset_x * offset_scale
                media_triangle[:, 1] -= transform.offset_y * offset_scale

                dest_points = mask.vertices.astype(np.float32)

                # Get affine transform for triangles
                M = cv2.getAffineTransform(media_triangle, dest_points)
                warped = cv2.warpAffine(transformed_media, M, (self.width, self.height),
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=(0, 0, 0))

                # Create mask for blending
                mask_img = np.zeros((self.height, self.width), dtype=np.uint8)
                cv2.fillPoly(mask_img, [dest_points.astype(np.int32)], 255)

                # Blend with output canvas
                mask_3ch = cv2.cvtColor(mask_img, cv2.COLOR_GRAY2BGR)
                self.output_canvas = np.where(mask_3ch > 0, warped, self.output_canvas)

            elif len(mask.vertices) >= 4:
                # For rectangles/quads, use perspective transform with 4 points
                dest_points = mask.vertices[:4].astype(np.float32)

                # Get homography
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

    def draw_grid(self, mask):
        """Draw grid around mask boundaries"""
        if not self.show_grid:
            return

        vertices = mask.vertices.astype(np.int32)

        # Draw polygon outline
        cv2.polylines(self.output_canvas, [vertices], True, (0, 255, 0), 2)

        # Draw vertices as circles
        for vertex in vertices:
            cv2.circle(self.output_canvas, tuple(vertex), 5, (0, 255, 0), -1)

    def toggle_grid(self):
        """Toggle grid visibility"""
        self.show_grid = not self.show_grid

