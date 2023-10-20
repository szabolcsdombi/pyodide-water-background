import struct

import js
import pyodide
import pyodide_js
import zengl

js.document.getElementById('loading').remove()
js.document.getElementsByClassName('terminal')[0].style.backgroundColor = 'transparent'
js.document.getElementsByClassName('terminal')[0].style.textShadow = 'black 1px 1px 1px, black 1px 1px 0'

width = js.window.innerWidth
height = js.window.innerHeight

canvas = js.document.createElement('canvas')
canvas.style.position = 'fixed'
canvas.style.top = '0'
canvas.style.left = '0'
canvas.style.width = width
canvas.style.height = width
canvas.width = width
canvas.height = height
canvas = js.document.body.insertBefore(canvas, js.document.body.children[0])

gl = canvas.getContext(
    'webgl2',
    powerPreference='high-performance',
    premultipliedAlpha=False,
    antialias=False,
    alpha=False,
    depth=False,
    stencil=False,
)

setup_gl = js.eval(zengl.setup_gl)
setup_gl(pyodide_js._module, gl)

ctx = zengl.context()

pipeline = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;

        vec2 positions[3] = vec2[](
            vec2(-1.0, -1.0),
            vec2(3.0, -1.0),
            vec2(-1.0, 3.0)
        );

        void main() {
            gl_Position = vec4(positions[gl_VertexID], 0.0, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;

        layout (location = 0) out vec4 out_color;

        uniform float iTime;
        uniform vec3 iResolution;

        // https://www.shadertoy.com/view/MdXyzX

        #define DRAG_MULT 0.1
        #define WATER_DEPTH 0.5
        #define CAMERA_HEIGHT 1.0
        #define ITERATIONS_RAYMARCH 5
        #define ITERATIONS_NORMAL 10

        vec2 wavedx(vec2 position, vec2 direction, float frequency, float timeshift) {
            float x = dot(direction, position) * frequency + timeshift;
            float wave = exp(sin(x) - 1.0);
            float dx = wave * cos(x);
            return vec2(wave, -dx);
        }

        float getwaves(vec2 position, int iterations) {
            float iter = 0.0;
            float frequency = 1.0;
            float timeMultiplier = 2.0;
            float weight = 1.0;
            float sumOfValues = 0.0;
            float sumOfWeights = 0.0;
            for(int i=0; i < iterations; i++) {
                vec2 p = vec2(sin(iter), cos(iter));
                vec2 res = wavedx(position, p, frequency, iTime * timeMultiplier);
                position += p * res.y * weight * DRAG_MULT;
                sumOfValues += res.x * weight;
                sumOfWeights += weight;
                weight *= 0.82;
                frequency *= 1.18;
                timeMultiplier *= 1.07;
                iter += 1232.399963;
            }
            return sumOfValues / sumOfWeights;
        }

        float raymarchwater(vec3 camera, vec3 start, vec3 end, float depth) {
            vec3 pos = start;
            vec3 dir = normalize(end - start);
            for(int i=0; i < 64; i++) {
                float height = getwaves(pos.xz, ITERATIONS_RAYMARCH) * depth - depth;
                if (height + 0.01 > pos.y) {
                    return distance(pos, camera);
                }
                pos += dir * (pos.y - height);
            }
            return distance(start, camera);
        }

        vec3 normal(vec2 pos, float e, float depth) {
            vec2 ex = vec2(e, 0);
            float H = getwaves(pos.xy, ITERATIONS_NORMAL) * depth;
            vec3 a = vec3(pos.x, H, pos.y);
            return normalize(
                cross(
                    a - vec3(pos.x - e, getwaves(pos.xy - ex.xy, ITERATIONS_NORMAL) * depth, pos.y),
                    a - vec3(pos.x, getwaves(pos.xy + ex.yx, ITERATIONS_NORMAL) * depth, pos.y + e)
                )
            );
        }

        mat3 createRotationMatrixAxisAngle(vec3 axis, float angle) {
            float s = sin(angle);
            float c = cos(angle);
            float oc = 1.0 - c;
            return mat3(
                oc * axis.x * axis.x + c, oc * axis.x * axis.y - axis.z * s, oc * axis.z * axis.x + axis.y * s,
                oc * axis.x * axis.y + axis.z * s, oc * axis.y * axis.y + c, oc * axis.y * axis.z - axis.x * s,
                oc * axis.z * axis.x - axis.y * s, oc * axis.y * axis.z + axis.x * s, oc * axis.z * axis.z + c
            );
        }

        vec3 getRay(vec2 fragCoord) {
            vec2 uv = ((fragCoord.xy / iResolution.xy) * 2.0 - 1.0) * vec2(iResolution.x / iResolution.y, 1.0);
            vec3 proj = normalize(vec3(uv.x, uv.y, 1.5));
            return createRotationMatrixAxisAngle(vec3(0.0, -1.0, 0.0), 3.0 * ((0.0 + 0.5) * 2.0 - 1.0))
                * createRotationMatrixAxisAngle(vec3(1.0, 0.0, 0.0), 0.5 + 1.5 * ((0.22 * 1.5) * 2.0 - 1.0))
                * proj;
        }

        float intersectPlane(vec3 origin, vec3 direction, vec3 point, vec3 normal) {
            return clamp(dot(point - origin, normal) / dot(direction, normal), -1.0, 9991999.0);
        }

        vec3 extra_cheap_atmosphere(vec3 raydir, vec3 sundir) {
            sundir.y = max(sundir.y, -0.07);
            float special_trick = 1.0 / (raydir.y * 1.0 + 0.1);
            float special_trick2 = 1.0 / (sundir.y * 11.0 + 1.0);
            float raysundt = pow(abs(dot(sundir, raydir)), 2.0);
            float sundt = pow(max(0.0, dot(sundir, raydir)), 8.0);
            float mymie = sundt * special_trick * 0.2;
            vec3 suncolor = mix(vec3(1.0), max(vec3(0.0), vec3(1.0) - vec3(5.5, 13.0, 22.4) / 22.4), special_trick2);
            vec3 bluesky= vec3(5.5, 13.0, 22.4) / 22.4 * suncolor;
            vec3 bluesky2 = max(vec3(0.0), bluesky - vec3(5.5, 13.0, 22.4) * 0.002 * (special_trick + -6.0 * sundir.y * sundir.y));
            bluesky2 *= special_trick * (0.24 + raysundt * 0.24);
            return bluesky2 * (1.0 + 1.0 * pow(1.0 - raydir.y, 3.0)) + mymie * suncolor;
        }

        vec3 getSunDirection() {
            return vec3(0, 0.316228, 0.948683);
        }

        vec3 getAtmosphere(vec3 dir) {
            return extra_cheap_atmosphere(dir, getSunDirection()) * 0.5;
        }

        float getSun(vec3 dir) {
            return pow(max(0.0, dot(dir, getSunDirection())), 720.0) * 210.0;
        }

        vec3 aces_tonemap(vec3 color) {
            mat3 m1 = mat3(0.59719, 0.07600, 0.02840, 0.35458, 0.90834, 0.13383, 0.04823, 0.01566, 0.83777);
            mat3 m2 = mat3(1.60475, -0.10208, -0.00327, -0.53108, 1.10813, -0.07276, -0.07367, -0.00605, 1.07602);
            vec3 v = m1 * color;
            vec3 a = v * (v + 0.0245786) - 0.000090537;
            vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081;
            return pow(clamp(m2 * (a / b), 0.0, 1.0), vec3(1.0 / 2.2));
        }

        void mainImage(out vec4 fragColor, in vec2 fragCoord) {
            vec3 ray = getRay(fragCoord);
            if (ray.y >= 0.0) {
                vec3 C = getAtmosphere(ray) + getSun(ray);
                fragColor = vec4(aces_tonemap(C * 2.0),1.0);
                return;
            }
            vec3 waterPlaneHigh = vec3(0.0, 0.0, 0.0);
            vec3 waterPlaneLow = vec3(0.0, -WATER_DEPTH, 0.0);
            vec3 origin = vec3(0.0, CAMERA_HEIGHT, iTime * 1.0);
            float highPlaneHit = intersectPlane(origin, ray, waterPlaneHigh, vec3(0.0, 1.0, 0.0));
            float lowPlaneHit = intersectPlane(origin, ray, waterPlaneLow, vec3(0.0, 1.0, 0.0));
            vec3 highHitPos = origin + ray * highPlaneHit;
            vec3 lowHitPos = origin + ray * lowPlaneHit;
            float dist = raymarchwater(origin, highHitPos, lowHitPos, WATER_DEPTH);
            vec3 waterHitPos = origin + ray * dist;
            vec3 N = normal(waterHitPos.xz, 0.01, WATER_DEPTH);
            N = mix(N, vec3(0.0, 1.0, 0.0), 0.8 * min(1.0, sqrt(dist*0.01) * 1.1));
            float fresnel = (0.04 + (1.0-0.04)*(pow(1.0 - max(0.0, dot(-N, ray)), 5.0)));
            vec3 R = normalize(reflect(ray, N));
            R.y = abs(R.y);
            vec3 reflection = getAtmosphere(R) + getSun(R);
            vec3 scattering = vec3(0.0293, 0.0698, 0.1717) * (0.2 + (waterHitPos.y + WATER_DEPTH) / WATER_DEPTH);
            vec3 C = fresnel * reflection + (1.0 - fresnel) * scattering;
            fragColor = vec4(aces_tonemap(C * 2.0), 1.0);
        }

        void main() {
            mainImage(out_color, vec2(gl_FragCoord.xy));
        }
    ''',
    uniforms={
        'iTime': 0.0,
        'iResolution': [width, height, 0.0],
    },
    framebuffer=None,
    viewport=(0, 0, width, height),
    topology='triangles',
    vertex_count=3,
)


@pyodide.ffi.create_proxy
def render(timestamp=0.0):
    ctx.new_frame()
    pipeline.uniforms['iTime'][:] = struct.pack('f', timestamp / 1000.0)
    pipeline.render()
    ctx.end_frame()
    js.requestAnimationFrame(render)


render()
