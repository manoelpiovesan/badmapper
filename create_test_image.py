import cv2
import numpy as np

# Create a test image with gradient and grid
width, height = 800, 600

# Create gradient background
img = np.zeros((height, width, 3), dtype=np.uint8)
for i in range(height):
    color_val = int((i / height) * 255)
    img[i, :] = [color_val, 100, 255 - color_val]

# Add grid lines
for i in range(0, width, 50):
    cv2.line(img, (i, 0), (i, height), (255, 255, 255), 1)
for j in range(0, height, 50):
    cv2.line(img, (0, j), (width, j), (255, 255, 255), 1)

# Add text
cv2.putText(img, 'BadMapper3 Test Image', (width//2 - 200, height//2),
            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

# Add circles in corners
cv2.circle(img, (100, 100), 50, (0, 255, 0), -1)
cv2.circle(img, (width-100, 100), 50, (255, 0, 0), -1)
cv2.circle(img, (100, height-100), 50, (0, 0, 255), -1)
cv2.circle(img, (width-100, height-100), 50, (255, 255, 0), -1)

# Save
cv2.imwrite('test_image.png', img)
print("Test image created: test_image.png")
