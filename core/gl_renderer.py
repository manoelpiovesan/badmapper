"""
OpenGL-accelerated renderer for high-performance video/media processing
"""
import cv2
import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
import ctypes


class GLRenderer:
    """Hardware-accelerated OpenGL renderer for masks and media"""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.show_grid = False
        self.textures = {}  # Cache textures by mask id
        self.initialized = False

        # Vertex and fragment shaders
        self.vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec2 aPos;
        layout (location = 1) in vec2 aTexCoord;

        out vec2 TexCoord;

        uniform mat3 uTransform;

        void main()
        {
            vec3 transformed = uTransform * vec3(aPos, 1.0);
            gl_Position = vec4(transformed.xy, 0.0, 1.0);
            TexCoord = aTexCoord;
        }
        """

        self.fragment_shader_source = """
        #version 330 core
        out vec4 FragColor;

        in vec2 TexCoord;

        uniform sampler2D texture1;
        uniform float alpha;

        void main()
        {
            FragColor = texture(texture1, TexCoord) * vec4(1.0, 1.0, 1.0, alpha);
        }
        """

        # Grid shader
        self.grid_vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec2 aPos;

        uniform mat3 uTransform;

        void main()
        {
            vec3 transformed = uTransform * vec3(aPos, 1.0);
            gl_Position = vec4(transformed.xy, 0.0, 1.0);
        }
        """

        self.grid_fragment_shader_source = """
        #version 330 core
        out vec4 FragColor;

        uniform vec3 color;

        void main()
        {
            FragColor = vec4(color, 1.0);
        }
        """

    def initialize(self):
        """Initialize OpenGL resources"""
        if self.initialized:
            return

        try:
            # Compile shaders
            vertex_shader = shaders.compileShader(self.vertex_shader_source, GL_VERTEX_SHADER)
            fragment_shader = shaders.compileShader(self.fragment_shader_source, GL_FRAGMENT_SHADER)
            self.shader_program = shaders.compileProgram(vertex_shader, fragment_shader)

            # Compile grid shaders
            grid_vertex_shader = shaders.compileShader(self.grid_vertex_shader_source, GL_VERTEX_SHADER)
            grid_fragment_shader = shaders.compileShader(self.grid_fragment_shader_source, GL_FRAGMENT_SHADER)
            self.grid_shader_program = shaders.compileProgram(grid_vertex_shader, grid_fragment_shader)

            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # Setup VAO and VBO for quad
            self.vao = glGenVertexArrays(1)
            self.vbo = glGenBuffers(1)

            glBindVertexArray(self.vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)

            # Quad vertices with texture coordinates
            # Positions (x, y) and TexCoords (s, t)
            quad_vertices = np.array([
                # positions  # texture coords
                0.0, 0.0,    0.0, 1.0,
                1.0, 0.0,    1.0, 1.0,
                1.0, 1.0,    1.0, 0.0,
                0.0, 1.0,    0.0, 0.0,
            ], dtype=np.float32)

            glBufferData(GL_ARRAY_BUFFER, quad_vertices.nbytes, quad_vertices, GL_STATIC_DRAW)

            # Position attribute
            glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))
            glEnableVertexAttribArray(0)

            # Texture coord attribute
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(2 * 4))
            glEnableVertexAttribArray(1)

            # Setup VAO for grid lines
            self.grid_vao = glGenVertexArrays(1)
            self.grid_vbo = glGenBuffers(1)

            glBindVertexArray(0)

            self.initialized = True
        except Exception as e:
            print(f"Warning: Failed to initialize OpenGL renderer: {e}")
            print("Falling back to CPU renderer")
            self.initialized = False

    def reset_canvas(self):
        """Clear the canvas"""
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

    def upload_texture(self, mask_id, frame):
        """Upload frame to GPU as texture"""
        if frame is None:
            return None

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb_frame.shape[:2]

        # Reuse texture if it exists
        if mask_id in self.textures:
            texture_id = self.textures[mask_id]
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, rgb_frame)
        else:
            # Create new texture
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)

            # Set texture parameters
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            # Upload texture data
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, rgb_frame)

            self.textures[mask_id] = texture_id

        return texture_id

    def create_transform_matrix(self, mask, frame_shape):
        """Create transformation matrix from media space to normalized device coordinates"""
        media_h, media_w = frame_shape[:2]
        transform = mask.media_transform

        # Start with media quad corners
        src_points = np.array([
            [0, 0],
            [media_w, 0],
            [media_w, media_h],
            [0, media_h]
        ], dtype=np.float32)

        # Apply media transformations
        center = np.array([media_w / 2, media_h / 2])

        # Apply rotation
        if transform.rotation != 0:
            angle_rad = np.radians(transform.rotation)
            cos_a = np.cos(angle_rad)
            sin_a = np.sin(angle_rad)
            for i in range(4):
                p = src_points[i] - center
                src_points[i] = np.array([
                    p[0] * cos_a - p[1] * sin_a,
                    p[0] * sin_a + p[1] * cos_a
                ]) + center

        # Apply scale
        if transform.scale != 1.0:
            for i in range(4):
                p = src_points[i] - center
                src_points[i] = p * transform.scale + center

        # Apply offset
        offset_scale = 0.5
        src_points[:, 0] -= transform.offset_x * offset_scale
        src_points[:, 1] -= transform.offset_y * offset_scale

        # Get destination points (mask vertices in screen space)
        if len(mask.vertices) >= 4:
            dst_points = mask.vertices[:4].astype(np.float32)
        elif len(mask.vertices) == 3:
            # For triangles, create a degenerate quad
            dst_points = np.vstack([mask.vertices, mask.vertices[2]]).astype(np.float32)
        else:
            return None

        # Convert to normalized device coordinates (-1 to 1)
        dst_points_ndc = dst_points.copy()
        dst_points_ndc[:, 0] = (dst_points[:, 0] / self.width) * 2.0 - 1.0
        dst_points_ndc[:, 1] = 1.0 - (dst_points[:, 1] / self.height) * 2.0

        # Compute perspective transform
        # We want to map unit quad [0,1]x[0,1] to dst_points_ndc
        src_unit = np.array([
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1]
        ], dtype=np.float32)

        try:
            H = cv2.getPerspectiveTransform(src_unit, dst_points_ndc)
            return H
        except:
            return None

    def render_mask(self, mask):
        """Render a mask with its media using OpenGL"""
        if not self.initialized:
            self.initialize()

        if mask.media is None:
            return

        frame = mask.media.get_current_frame()
        if frame is None:
            return

        # Upload texture
        texture_id = self.upload_texture(id(mask), frame)
        if texture_id is None:
            return

        # Create transformation matrix
        transform_matrix = self.create_transform_matrix(mask, frame.shape)
        if transform_matrix is None:
            return

        # Use shader program
        glUseProgram(self.shader_program)

        # Bind texture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glUniform1i(glGetUniformLocation(self.shader_program, "texture1"), 0)
        glUniform1f(glGetUniformLocation(self.shader_program, "alpha"), 1.0)

        # Set transform matrix
        transform_loc = glGetUniformLocation(self.shader_program, "uTransform")
        glUniformMatrix3fv(transform_loc, 1, GL_TRUE, transform_matrix)

        # Draw quad
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        glBindVertexArray(0)

    def draw_grid(self, mask):
        """Draw grid around mask boundaries using OpenGL"""
        if not self.initialized or not self.show_grid:
            return

        glUseProgram(self.grid_shader_program)

        # Convert vertices to NDC
        vertices = mask.vertices.astype(np.float32)
        vertices_ndc = np.zeros_like(vertices)
        vertices_ndc[:, 0] = (vertices[:, 0] / self.width) * 2.0 - 1.0
        vertices_ndc[:, 1] = 1.0 - (vertices[:, 1] / self.height) * 2.0

        # Identity transform
        identity = np.eye(3, dtype=np.float32)
        transform_loc = glGetUniformLocation(self.grid_shader_program, "uTransform")
        glUniformMatrix3fv(transform_loc, 1, GL_TRUE, identity)

        # Set color
        color_loc = glGetUniformLocation(self.grid_shader_program, "color")
        glUniform3f(color_loc, 0.0, 1.0, 0.0)

        # Draw lines
        glBindVertexArray(self.grid_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.grid_vbo)

        # Create line loop vertices
        line_vertices = np.zeros(len(vertices_ndc) * 2, dtype=np.float32)
        for i, v in enumerate(vertices_ndc):
            line_vertices[i*2] = v[0]
            line_vertices[i*2 + 1] = v[1]

        glBufferData(GL_ARRAY_BUFFER, line_vertices.nbytes, line_vertices, GL_DYNAMIC_DRAW)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glLineWidth(2.0)
        glDrawArrays(GL_LINE_LOOP, 0, len(vertices))

        # Draw vertices as points
        glPointSize(10.0)
        glDrawArrays(GL_POINTS, 0, len(vertices))

        glBindVertexArray(0)

    def toggle_grid(self):
        """Toggle grid visibility"""
        self.show_grid = not self.show_grid

    def cleanup(self):
        """Clean up OpenGL resources"""
        if self.initialized:
            # Delete textures
            for texture_id in self.textures.values():
                glDeleteTextures(1, [texture_id])
            self.textures.clear()

            # Delete buffers and VAOs
            glDeleteVertexArrays(1, [self.vao])
            glDeleteBuffers(1, [self.vbo])
            glDeleteVertexArrays(1, [self.grid_vao])
            glDeleteBuffers(1, [self.grid_vbo])

            # Delete shaders
            glDeleteProgram(self.shader_program)
            glDeleteProgram(self.grid_shader_program)

            self.initialized = False
