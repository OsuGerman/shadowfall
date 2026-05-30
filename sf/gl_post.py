"""OpenGL Post-Process-Layer (Update #171).

Hybrid-Architektur: Pygame rendert die gesamte 2D-Welt wie bisher in eine
Off-Screen-Surface. Dieses Modul nimmt die Surface als OpenGL-Texture und
appliziert per GLSL-Fragment-Shader einen Post-Process-Pass (Bloom +
Color-Grade + Vignette + optionale Screen-Shake-Distortion).

Wenn PyOpenGL nicht verfuegbar ist ODER der User es im Settings deaktiviert
hat, faellt die Engine elegant auf Direct-Pygame-Blit zurueck (keine
Aenderung am Look).

Architektur:
    Game-Loop:
      1. Pygame-Update (wie bisher)
      2. Pygame-Draw to self._render_surface  (Off-Screen-Surface)
      3. GLPostProcessor.present(render_surface, biome=..., shake=...)
         a) Upload surface → GL-Texture
         b) Fullscreen-Quad mit Fragment-Shader rendern
         c) pygame.display.flip()  (im OPENGL-Modus)
      ODER (wenn disabled):
         self.screen.blit(render_surface, (0, 0))  + flip()

Tools die in unserem Stack davon profitieren:
- Aspekt-Aura-Glows (Cast-Anim) → Bloom verstaerkt sie automatisch
- Lava-Crack-Glow (Floor + Wall) → bloomed Heat-Wave
- Frost-Crystal-Highlights → kalter Tint
- Per-Biom-Color-Grade → Saturation/Contrast pro Biom
- Vignette → automatischer cinematischer Look

Doku: VELGRAD_RENDER_SPEC.md (Engine-Render-Section) + Settings-Menue
"""
from __future__ import annotations

import sys
import pygame

# Lazy-Import PyOpenGL — fehlt es, faellt die Engine auf Direct-Blit zurueck.
_GL_AVAILABLE = False
try:
    from OpenGL import GL as gl  # type: ignore
    _GL_AVAILABLE = True
except ImportError:
    pass


# ============================================================
# GLSL SHADER SOURCES
# ============================================================
VERTEX_SHADER = """
#version 130

in vec2 a_pos;
in vec2 a_uv;
out vec2 v_uv;

void main() {
    v_uv = a_uv;
    gl_Position = vec4(a_pos, 0.0, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 130

in vec2 v_uv;
uniform sampler2D u_tex;

// Color-Grade
uniform vec3 u_tint;          // RGB-Mult (1,1,1 = neutral)
uniform float u_contrast;     // 1.0 = neutral, >1 = punchier
uniform float u_saturation;   // 1.0 = neutral

// Bloom
uniform float u_bloom_strength;  // 0.0..1.5
uniform float u_bloom_threshold; // 0.0..1.0 — only pixels above this glow

// Vignette
uniform float u_vignette_strength;  // 0.0..0.6

// Screen-Shake (subtle UV displacement)
uniform vec2 u_shake_offset;        // small UV-offset (e.g. 0.001..0.005)

// Heat-Wave (per-pixel sinus-distortion fuer Lava-Biome)
uniform float u_heat_amplitude;     // 0.0 = off
uniform float u_time;               // for animation

out vec4 fragColor;

vec3 _sample_with_shake(vec2 uv) {
    return texture(u_tex, uv + u_shake_offset).rgb;
}

vec3 _bloom(vec2 uv) {
    // Update #193: ECHTER additiver Gaussian-Blur (kein /total mehr).
    // Vorher: sum /= total normierte das Resultat → bei Text gab es
    // ein helles Echo des Glyphs in Nachbarpixeln = sichtbares Doppel-Bild.
    // Jetzt: jeder bright pixel addiert seine Helligkeit gewichtet, ohne
    // Re-Normalisierung — ergibt einen weichen Halo statt einer Kopie.
    vec3 sum = vec3(0.0);
    float radius = 0.0025;
    // 9-tap gewichtetes Sample-Kernel (zentriert mehr Gewicht, abnehmend nach aussen)
    const float w_center = 0.25;
    const float w_edge   = 0.125;
    const float w_diag   = 0.0625;
    // Center
    {
        vec3 s = texture(u_tex, uv).rgb;
        float br = max(s.r, max(s.g, s.b));
        sum += s * max(0.0, br - u_bloom_threshold) * w_center;
    }
    // Cardinal (4 taps)
    vec2 cards[4];
    cards[0] = vec2( 1.0, 0.0);
    cards[1] = vec2(-1.0, 0.0);
    cards[2] = vec2( 0.0, 1.0);
    cards[3] = vec2( 0.0,-1.0);
    for (int i = 0; i < 4; i++) {
        vec3 s = texture(u_tex, uv + cards[i] * radius).rgb;
        float br = max(s.r, max(s.g, s.b));
        sum += s * max(0.0, br - u_bloom_threshold) * w_edge;
    }
    // Diagonal (4 taps)
    vec2 diags[4];
    diags[0] = vec2( 1.0, 1.0);
    diags[1] = vec2( 1.0,-1.0);
    diags[2] = vec2(-1.0, 1.0);
    diags[3] = vec2(-1.0,-1.0);
    for (int i = 0; i < 4; i++) {
        vec3 s = texture(u_tex, uv + diags[i] * radius * 1.4).rgb;
        float br = max(s.r, max(s.g, s.b));
        sum += s * max(0.0, br - u_bloom_threshold) * w_diag;
    }
    return sum * u_bloom_strength;
}

void main() {
    vec2 uv = v_uv;

    // Heat-Wave Distortion (Lava-Biome)
    if (u_heat_amplitude > 0.0) {
        float dy = sin(uv.x * 40.0 + u_time * 3.0) * u_heat_amplitude;
        uv.y += dy;
    }

    vec3 base = _sample_with_shake(uv);
    vec3 bloom = _bloom(uv);
    vec3 col = base + bloom;

    // Color-Grade: Saturation
    float gray = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(gray), col, u_saturation);

    // Color-Grade: Contrast (centered around 0.5)
    col = (col - 0.5) * u_contrast + 0.5;

    // Color-Grade: Tint (per-biome RGB-Multiplier)
    col *= u_tint;

    // Vignette (radial darken to corners)
    vec2 vd = v_uv - vec2(0.5);
    float vdist = dot(vd, vd) * 2.0;   // 0 center, ~1 corners
    float vfactor = 1.0 - vdist * u_vignette_strength;
    col *= clamp(vfactor, 0.0, 1.0);

    fragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
"""


# ============================================================
# PER-BIOM COLOR-GRADE PROFILES
# ============================================================
# Subtile Mood-Shifts pro Biom — Saturation, Contrast, Tint.
# Keine drastische Faerbung, nur 5-15% Adjustments.
BIOME_GRADE = {
    'crypt':        {'tint': (0.92, 0.95, 1.05),  'contrast': 1.08, 'saturation': 0.92, 'heat': 0.0},
    'frost':        {'tint': (0.90, 0.98, 1.12),  'contrast': 1.05, 'saturation': 0.85, 'heat': 0.0},
    'lava':         {'tint': (1.08, 0.92, 0.85),  'contrast': 1.12, 'saturation': 1.10, 'heat': 0.0025},
    'swamp':        {'tint': (0.88, 1.02, 0.92),  'contrast': 1.05, 'saturation': 0.95, 'heat': 0.0},
    'astral':       {'tint': (1.02, 0.92, 1.15),  'contrast': 1.08, 'saturation': 1.10, 'heat': 0.0},
    'desert':       {'tint': (1.08, 1.02, 0.88),  'contrast': 1.06, 'saturation': 0.95, 'heat': 0.001},
    'town':         {'tint': (1.0, 1.0, 1.0),     'contrast': 1.0,  'saturation': 1.0,  'heat': 0.0},
    'wound_salt':   {'tint': (1.05, 1.0, 0.98),   'contrast': 1.08, 'saturation': 0.90, 'heat': 0.0},
    'wound_ash':    {'tint': (1.05, 0.95, 0.88),  'contrast': 1.10, 'saturation': 0.85, 'heat': 0.002},
    'wound_hollow': {'tint': (0.95, 0.95, 1.08),  'contrast': 1.12, 'saturation': 1.05, 'heat': 0.0},
    'hollow_word':  {'tint': (1.06, 1.00, 1.05),  'contrast': 1.10, 'saturation': 1.05, 'heat': 0.0},
}

# Default-Grade wenn Biome nicht registriert
DEFAULT_GRADE = {'tint': (1.0, 1.0, 1.0), 'contrast': 1.0, 'saturation': 1.0, 'heat': 0.0}


# ============================================================
# POST-PROCESSOR
# ============================================================
class GLPostProcessor:
    """Wrappt PyOpenGL fuer einen einzigen Post-Process-Pass.

    Usage:
        post = GLPostProcessor(width=1600, height=900)
        post.init()   # creates GL context-resources

        # Each frame after pygame.draw:
        post.present(self._render_surface, biome='crypt', shake=12.0)

    Wenn PyOpenGL fehlt, init() returnt False — Aufrufer faellt auf
    Direct-Blit zurueck.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.enabled = False    # gesetzt durch init() wenn ok
        self.shader_program = 0
        self.vao = 0
        self.vbo = 0
        self.tex = 0
        # Update #193: Bloom moderater (war 0.5 → sichtbares Echo bei Text).
        # Threshold hoch damit nur echte Highlights bluehen, nicht Body-Text.
        self.bloom_strength = 0.35
        self.bloom_threshold = 0.85
        self.vignette_strength = 0.30

    # ----------------------------------------------------------------
    def init(self) -> bool:
        """Erstellt GL-Resources. Returnt True bei Erfolg, False bei Fehler.

        WICHTIG: Pygame muss VOR diesem Call mit OPENGL-Flag initialisiert
        sein:
            screen = pygame.display.set_mode(
                (w, h), pygame.OPENGL | pygame.DOUBLEBUF)
        """
        if not _GL_AVAILABLE:
            print('  gl_post: PyOpenGL nicht verfuegbar, Post-Process disabled.',
                  file=sys.stderr)
            return False
        try:
            self.shader_program = self._compile_shaders()
            self.vao, self.vbo = self._create_fullscreen_quad()
            self.tex = self._create_texture()
            gl.glDisable(gl.GL_DEPTH_TEST)
            self.enabled = True
            return True
        except Exception as e:
            print(f'  gl_post: init failed: {e}', file=sys.stderr)
            return False

    # ----------------------------------------------------------------
    def _compile_shaders(self) -> int:
        """Compile + link Vertex+Fragment-Shader. Returnt Program-ID."""
        from OpenGL.GL import shaders
        vs = shaders.compileShader(VERTEX_SHADER, gl.GL_VERTEX_SHADER)
        fs = shaders.compileShader(FRAGMENT_SHADER, gl.GL_FRAGMENT_SHADER)
        program = shaders.compileProgram(vs, fs)
        return program

    # ----------------------------------------------------------------
    def _create_fullscreen_quad(self) -> tuple[int, int]:
        """Vertex-Buffer + VAO fuer 2 Triangles, die den ganzen Screen fuellen.
        Pro Vertex: 2x pos, 2x uv. Returnt (vao, vbo)."""
        import numpy as np
        # Triangle-Strip: (-1,-1) (1,-1) (-1,1) (1,1)
        # UV: (0,1) (1,1) (0,0) (1,0)   — Y flipped weil Pygame top-down
        vertices = np.array([
            #  pos x, pos y,  uv x, uv y
            -1.0, -1.0,  0.0, 1.0,
             1.0, -1.0,  1.0, 1.0,
            -1.0,  1.0,  0.0, 0.0,
             1.0,  1.0,  1.0, 0.0,
        ], dtype=np.float32)

        vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(vao)
        vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes,
                         vertices, gl.GL_STATIC_DRAW)
        # a_pos: location 0, vec2
        loc_pos = gl.glGetAttribLocation(self.shader_program, 'a_pos')
        loc_uv = gl.glGetAttribLocation(self.shader_program, 'a_uv')
        stride = 4 * 4  # 4 floats x 4 bytes
        gl.glEnableVertexAttribArray(loc_pos)
        gl.glVertexAttribPointer(loc_pos, 2, gl.GL_FLOAT, gl.GL_FALSE,
                                  stride, gl.ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(loc_uv)
        gl.glVertexAttribPointer(loc_uv, 2, gl.GL_FLOAT, gl.GL_FALSE,
                                  stride, gl.ctypes.c_void_p(8))
        gl.glBindVertexArray(0)
        return vao, vbo

    # ----------------------------------------------------------------
    def _create_texture(self) -> int:
        tex = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, self.width, self.height,
                         0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, None)
        return tex

    # ----------------------------------------------------------------
    def upload_surface(self, surf: pygame.Surface) -> None:
        """Pygame-Surface → GL-Texture-Upload.

        Update #192-fix: KEIN Vertical-Flip mehr beim Upload (3. Arg
        False). Die UV-Koords in _create_fullscreen_quad sind bereits
        Y-geflippt fuer Pygame's top-down Layout — vorheriger doppel-
        Flip → Bild stand auf dem Kopf.
        """
        data = pygame.image.tostring(surf, 'RGB', False)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex)
        gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0,
                            self.width, self.height,
                            gl.GL_RGB, gl.GL_UNSIGNED_BYTE, data)

    # ----------------------------------------------------------------
    def present(self, surface: pygame.Surface, *,
                 biome: str = 'town',
                 shake_amount: float = 0.0,
                 time_sec: float = 0.0) -> None:
        """Renders the surface with post-process effects + swaps buffers.

        biome:          Color-Grade-Profile-Key (BIOME_GRADE)
        shake_amount:   0..30, kleine UV-Offset-Distortion fuer Screen-Shake
        time_sec:       fuer Heat-Wave-Animation
        """
        if not self.enabled:
            return
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glViewport(0, 0, self.width, self.height)

        self.upload_surface(surface)

        gl.glUseProgram(self.shader_program)
        # Bind Texture
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex)
        loc = gl.glGetUniformLocation(self.shader_program, 'u_tex')
        gl.glUniform1i(loc, 0)

        # Color-Grade Uniforms
        grade = BIOME_GRADE.get(biome, DEFAULT_GRADE)
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, 'u_tint'),
                        *grade['tint'])
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, 'u_contrast'),
                        grade['contrast'])
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, 'u_saturation'),
                        grade['saturation'])

        # Bloom
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, 'u_bloom_strength'),
                        self.bloom_strength)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, 'u_bloom_threshold'),
                        self.bloom_threshold)

        # Vignette
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, 'u_vignette_strength'),
                        self.vignette_strength)

        # Shake
        import math as _m
        if shake_amount > 0:
            t = time_sec * 60
            sx = _m.sin(t * 7.1) * shake_amount * 0.0005
            sy = _m.cos(t * 5.3) * shake_amount * 0.0005
        else:
            sx = sy = 0.0
        gl.glUniform2f(gl.glGetUniformLocation(self.shader_program, 'u_shake_offset'),
                        sx, sy)

        # Heat-Wave
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, 'u_heat_amplitude'),
                        grade['heat'])
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, 'u_time'),
                        time_sec)

        # Draw fullscreen quad
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)
        gl.glBindVertexArray(0)

        pygame.display.flip()

    # ----------------------------------------------------------------
    def teardown(self) -> None:
        # Update #201: PyOpenGL erwartet (n, ids)-Signatur fuer
        # glDeleteBuffers/Textures/VertexArrays.  Vorheriger 1-arg-Call
        # `glDeleteBuffers([self.vbo])` crashte mit
        # `requires 2 arguments (n, buffers), received 1`.
        # Try/except pro Resource damit ein Fehler nicht die anderen
        # Cleanups blockt (teardown wird beim fullscreen-Toggle aufgerufen).
        if self.tex:
            try:
                gl.glDeleteTextures(1, [self.tex])
            except Exception:
                pass
        if self.vbo:
            try:
                gl.glDeleteBuffers(1, [self.vbo])
            except Exception:
                pass
        if self.vao:
            try:
                gl.glDeleteVertexArrays(1, [self.vao])
            except Exception:
                pass
        if self.shader_program:
            try:
                gl.glDeleteProgram(self.shader_program)
            except Exception:
                pass
        self.enabled = False


# ============================================================
# CONVENIENCE: Module-level Singleton (Engine waehlt: enabled oder nicht)
# ============================================================
_active_processor: GLPostProcessor | None = None


def get_active() -> GLPostProcessor | None:
    """Returnt den aktiven Post-Processor (oder None wenn disabled)."""
    return _active_processor


def install(width: int, height: int) -> bool:
    """Tries to set up the global processor. Returnt True bei Erfolg.
    Wenn False, sollte die Engine pygame-Direct-Blit verwenden."""
    global _active_processor
    if not _GL_AVAILABLE:
        return False
    proc = GLPostProcessor(width, height)
    if not proc.init():
        return False
    _active_processor = proc
    return True


def uninstall() -> None:
    global _active_processor
    if _active_processor is not None:
        _active_processor.teardown()
        _active_processor = None


def is_available() -> bool:
    """True wenn PyOpenGL importierbar (egal ob initialisiert)."""
    return _GL_AVAILABLE
