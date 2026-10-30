// Pose monitor: the camera picture with the stage zones and the body drawn
// over it, a zone strip below, and bars for the pose signals on the right.
// Values come from panel_values through values_tex: texel (0, k), k in the
// order of panel_values_callbacks (VALUES, then 33 landmarks as x, y, vis).
// Input 1 is MediaPipe's video (shown only while Source is Camera), input 2
// the text from text_labels (white on transparent; coloured here). Layout
// numbers come from labels_callbacks.

uniform vec4 uLayout;  // picture width, picture height, right column x, centre of the first bar row
uniform vec4 uRows;    // row height, pad, -, -

layout(location = 0) out vec4 fragColor;

const int PRESENT = 0, IMAGEX = 1, HAND_L = 2, HAND_R = 3, SPREAD = 4, ENERGY = 5;
const int ZONE = 6, ZONES = 7, MARGIN = 8, FLIP = 9, SOURCE = 10, SEEN = 11, POINTS = 12;
const int NUM_BONES = 12;
const ivec2 BONES[NUM_BONES] = ivec2[](
    ivec2(11, 12), ivec2(11, 13), ivec2(13, 15), ivec2(12, 14), ivec2(14, 16), ivec2(11, 23),
    ivec2(12, 24), ivec2(23, 24), ivec2(23, 25), ivec2(25, 27), ivec2(24, 26), ivec2(26, 28));
const float BAR_H = 16.0;

const vec3 BG = vec3(0.035, 0.04, 0.05);
const vec3 CARD = vec3(0.075, 0.085, 0.10);
const vec3 TRACK = vec3(0.13, 0.145, 0.165);
const vec3 TICK = vec3(0.30, 0.32, 0.36);
const vec3 TEXT = vec3(0.86, 0.88, 0.90);
const vec3 DIM = vec3(0.36, 0.39, 0.44);
const vec3 C_LIVE = vec3(0.45, 0.85, 0.60);
const vec3 C_ZONE = vec3(1.00, 0.70, 0.25);
const vec3 C_BODY = vec3(0.30, 0.82, 0.76);
const vec3 C_BAR[5] = vec3[](vec3(1.00, 0.70, 0.25), vec3(0.42, 0.60, 1.00), vec3(0.92, 0.38, 0.38),
    vec3(0.76, 0.62, 0.96), vec3(0.42, 0.85, 0.48));

float value(int k) {
    return texelFetch(sTD2DInputs[0], ivec2(0, k), 0).r;
}

// Landmark i in picture pixels (image y runs top to bottom).
vec2 landmark(int i, vec2 size, float top) {
    return vec2(value(POINTS + 3 * i) * size.x, top - value(POINTS + 3 * i + 1) * size.y);
}

float seen(int i) {
    return value(POINTS + 3 * i + 2) >= 0.5 ? 1.0 : 0.0;
}

float segment(vec2 p, vec2 a, vec2 b) {
    vec2 ab = b - a;
    float t = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-4), 0.0, 1.0);
    return length(p - a - ab * t);
}

void main() {
    vec2 p = gl_FragCoord.xy;
    vec2 res = uTDOutputInfo.res.zw;
    vec2 picture = uLayout.xy;
    float stripH = res.y - picture.y;
    float panelX = uLayout.z;
    float pad = uRows.y;
    int source = int(value(SOURCE) + 0.5);
    float present = value(PRESENT);
    int zones = clamp(int(value(ZONES) + 0.5), 1, 5);
    int zone = int(value(ZONE) + 0.5);
    bool flip = value(FLIP) > 0.5;
    float imageX = value(IMAGEX);

    vec3 col = BG;
    if (p.x < picture.x && p.y >= stripH) {
        // Camera picture (MediaPipe draws its own skeleton on it).
        vec2 uv = vec2(p.x / picture.x, (p.y - stripH) / picture.y);
        col = source == 1 ? texture(sTD2DInputs[1], uv).rgb : CARD;
        // Zone borders, with the margin band either side.
        float zoneW = picture.x / float(zones);
        for (int z = 1; z < 5; z++) {
            if (z >= zones) break;
            float bx = float(z) * zoneW;
            float band = value(MARGIN) * picture.x;
            if (abs(p.x - bx) < band) col = mix(col, C_ZONE, 0.10);
            if (abs(p.x - bx) < 1.5) col = mix(col, C_ZONE, 0.8);
        }
        // The dancer's position (hips) as a vertical line.
        if (present > 0.5 && abs(p.x - imageX * picture.x) < 1.5) col = mix(col, C_LIVE, 0.9);
        // Body: bones and joints from the landmarks.
        if (value(SEEN) > 0.5) {
            float top = res.y;
            float d = 1e4;
            for (int b = 0; b < NUM_BONES; b++) {
                ivec2 bone = BONES[b];
                if (seen(bone.x) * seen(bone.y) > 0.5)
                    d = min(d, segment(p, landmark(bone.x, picture, top), landmark(bone.y, picture, top)));
            }
            float line = 1.0 - smoothstep(2.0, 3.5, d);
            col = mix(col, C_BODY, line * 0.85);
            for (int i = 0; i < 33; i++) {
                // Head, arms and legs; the face and finger points are left out.
                if (seen(i) < 0.5 || (i > 0 && i < 11) || (i > 16 && i < 23) || i > 28) continue;
                float r = i == 0 ? 14.0 : 5.0;
                float dj = length(p - landmark(i, picture, top));
                col = mix(col, i == 0 ? C_BODY : TEXT, (1.0 - smoothstep(r - 1.5, r, dj)) * (i == 0 ? 0.5 : 0.9));
            }
        }
    } else if (p.x < picture.x) {
        // Zone strip: one block per zone, the dancer's zone lit, a dot at the position.
        float zoneW = picture.x / float(zones);
        int block = clamp(int(p.x / zoneW), 0, zones - 1);
        int blockZone = flip ? zones - block : block + 1;
        bool inBlock = p.x > float(block) * zoneW + 6.0 && p.x < float(block + 1) * zoneW - 6.0 && p.y > 12.0 && p.y < stripH - 12.0;
        if (inBlock) col = blockZone == zone && present > 0.5 ? mix(CARD, C_ZONE, 0.55) : CARD;
        if (present > 0.5 && length(p - vec2(imageX * picture.x, stripH * 0.22)) < 9.0) col = C_LIVE;
    } else {
        // Right column: status lamp and value bars.
        col = CARD;
        float x0 = panelX + pad;
        float x1 = res.x - pad;
        float lampOn = source != 0 && present > 0.5 ? 1.0 : 0.0;
        float dl = length(p - vec2(x0 + 10.0, res.y - 115.0));
        if (dl < 9.0) col = mix(TRACK, C_LIVE, lampOn);
        for (int r = 0; r < 5; r++) {
            float yc = uLayout.w - uRows.x * float(r) - 12.0;
            if (abs(p.y - yc) < BAR_H * 0.5 && p.x >= x0 && p.x < x1) {
                float v = clamp(value(r == 0 ? IMAGEX : r == 1 ? HAND_L : r == 2 ? HAND_R : r == 3 ? SPREAD : ENERGY), 0.0, 1.0);
                if (r == 0 && flip) v = 1.0 - v;
                col = p.x < x0 + v * (x1 - x0) && present > 0.5 ? C_BAR[r] : TRACK;
            }
        }
    }
    // Divider lines.
    if (abs(p.x - panelX) < 1.0 || (p.x < picture.x && abs(p.y - stripH) < 1.0)) col = TICK;

    float text = texelFetch(sTD2DInputs[2], ivec2(p), 0).a;
    vec3 textColor = p.x >= panelX ? TEXT : p.y < stripH ? TEXT : C_ZONE;
    if (p.x >= panelX && p.y > res.y - 60.0) textColor = TEXT;
    else if (p.x >= panelX && p.y > res.y - 95.0) textColor = DIM;
    col = mix(col, textColor, text);
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
