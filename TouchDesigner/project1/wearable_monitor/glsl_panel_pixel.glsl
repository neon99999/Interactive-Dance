// Wearable monitor: one card per wearable, a bar or lamp for every signal.
// Values come from panel_values through values_tex: texel (0, w * 12 + k), with
// k in the SIGNALS order of panel_values_callbacks. Layout numbers come from
// labels_callbacks, which also places the text in text_left and text_right
// (inputs 1 and 2, white on transparent; coloured here).

uniform vec4 uLayout;  // pad, header height, row height, label width (pixels)
uniform vec4 uRanges;  // value width (pixels), gyro range (dps), pitch range, roll range (deg)
uniform vec4 uSlots;   // number of cards, then the 0-based wearable in cards 0, 1, 2

layout(location = 0) out vec4 fragColor;

const int SIGNALS = 12;
const int LIVE = 0, MODE = 1, ACT = 2, GX = 3, GY = 4, GZ = 5, PITCH = 6, ROLL = 7, HIT = 8, STILL = 10, BTN = 11;
const float BAR_H = 14.0;
const float LAMP_R = 11.0;

const vec3 BG = vec3(0.035, 0.04, 0.05);
const vec3 CARD = vec3(0.075, 0.085, 0.10);
const vec3 TRACK = vec3(0.13, 0.145, 0.165);
const vec3 TICK = vec3(0.30, 0.32, 0.36);
const vec3 C_ACT = vec3(0.30, 0.82, 0.76);
const vec3 C_GX = vec3(0.92, 0.38, 0.38);
const vec3 C_GY = vec3(0.42, 0.85, 0.48);
const vec3 C_GZ = vec3(0.42, 0.60, 1.00);
const vec3 C_TILT = vec3(0.76, 0.62, 0.96);
const vec3 C_HIT = vec3(1.00, 0.56, 0.16);
const vec3 C_STILL = vec3(0.40, 0.62, 1.00);
const vec3 C_BTN = vec3(0.92, 0.92, 0.92);
const vec3 C_WRIST = vec3(0.30, 0.82, 0.76);
const vec3 C_ANKLE = vec3(1.00, 0.70, 0.25);
const vec3 C_LIVE = vec3(0.45, 0.85, 0.60);
const vec3 TEXT = vec3(0.86, 0.88, 0.90);
const vec3 DIM = vec3(0.36, 0.39, 0.44);

float value(int w, int k) {
    return texelFetch(sTD2DInputs[0], ivec2(0, w * SIGNALS + k), 0).r;
}

bool inRect(vec2 p, vec2 lo, vec2 hi) {
    return all(greaterThanEqual(p, lo)) && all(lessThan(p, hi));
}

void main() {
    vec2 p = gl_FragCoord.xy;
    vec2 res = uTDOutputInfo.res.zw;
    int cards = max(int(uSlots.x + 0.5), 1);
    float cardW = res.x / float(cards);
    int c = clamp(int(p.x / cardW), 0, cards - 1);
    int w = int((c == 0 ? uSlots.y : c == 1 ? uSlots.z : uSlots.w) + 0.5);
    float x0 = float(c) * cardW;
    float x1 = x0 + cardW;

    vec3 col = BG;
    if (!inRect(p, vec2(x0 + 8.0, 8.0), vec2(x1 - 8.0, res.y - 8.0))) {
        fragColor = TDOutputSwizzle(vec4(col, 1.0));
        return;
    }
    col = CARD;
    float live = value(w, LIVE) > 0.5 ? 1.0 : 0.0;

    // Mode stripe along the top of the card.
    int mode = int(value(w, MODE) + 0.5);
    vec3 modeColor = mode == 1 ? C_WRIST : mode == 2 ? C_ANKLE : TICK;
    if (p.y > res.y - 14.0) col = mix(TICK, modeColor, live);

    float pad = uLayout.x, header = uLayout.y, rowH = uLayout.z;
    float bx0 = x0 + pad + uLayout.w;
    float bx1 = x1 - pad - uRanges.x;
    float row = (res.y - header - p.y) / rowH;
    int r = int(floor(row));
    float yc = res.y - header - rowH * (float(r) + 0.5);

    if (row >= 0.0 && r < 9) {
        // Thin divider between rows.
        if (abs(p.y - (yc - rowH * 0.5)) < 0.5 && p.x > x0 + pad && p.x < x1 - pad) col = mix(CARD, TRACK, 0.8);

        if (r < 6) {
            int k = r == 0 ? ACT : r == 1 ? GX : r == 2 ? GY : r == 3 ? GZ : r == 4 ? PITCH : ROLL;
            vec3 barColor = r == 0 ? C_ACT : r == 1 ? C_GX : r == 2 ? C_GY : r == 3 ? C_GZ : C_TILT;
            float range = r == 0 ? 1.0 : r <= 3 ? uRanges.y : r == 4 ? uRanges.z : uRanges.w;
            float v = clamp(value(w, k) / range, r == 0 ? 0.0 : -1.0, 1.0) * live;
            if (abs(p.y - yc) < BAR_H * 0.5 && p.x >= bx0 && p.x < bx1) {
                col = TRACK;
                float start = r == 0 ? bx0 : 0.5 * (bx0 + bx1);
                float span = r == 0 ? bx1 - bx0 : 0.5 * (bx1 - bx0);
                float end = start + v * span;
                if (p.x >= min(start, end) && p.x < max(start, end)) col = barColor;
                if (r > 0 && abs(p.x - start) < 1.0) col = TICK;
            }
        } else {
            int k = r == 6 ? HIT : r == 7 ? STILL : BTN;
            vec3 lampColor = r == 6 ? C_HIT : r == 7 ? C_STILL : C_BTN;
            float on = (value(w, k) > 0.5 ? 1.0 : 0.0) * live;
            float d = length(p - vec2(bx0 + LAMP_R + 2.0, yc));
            float disc = 1.0 - smoothstep(LAMP_R - 1.0, LAMP_R, d);
            float ring = disc * smoothstep(LAMP_R - 3.0, LAMP_R - 2.0, d);
            float glow = on * exp(-max(d - LAMP_R, 0.0) / 6.0) * 0.35 * (1.0 - disc);
            col = mix(col, TICK, ring * (1.0 - on));
            col = mix(col, lampColor, disc * on);
            col += lampColor * glow;
        }
    }

    // A wearable with no signal fades back into the card.
    if (live < 0.5 && p.y < res.y - 14.0) col = mix(CARD, col, 0.45);

    // Text: white masks from text_left (labels, title) and text_right (values,
    // status), coloured here by what they say.
    ivec2 px = ivec2(p);
    float leftText = texelFetch(sTD2DInputs[1], px, 0).a;
    float rightText = texelFetch(sTD2DInputs[2], px, 0).a;
    bool inHeader = p.y > res.y - header;
    // Header: the mode name in its colour; the signal prefix line below it muted.
    bool titleLine = p.y > res.y - 80.0;
    vec3 leftColor = !inHeader ? TEXT : !titleLine ? mix(DIM, TEXT, 0.6) : p.x > x0 + pad + 56.0 ? modeColor : TEXT;
    vec3 rightColor = TEXT;
    if (inHeader) {
        rightColor = C_LIVE;
    } else if (r >= 6 && r < 9) {
        int k = r == 6 ? HIT : r == 7 ? STILL : BTN;
        vec3 lampColor = r == 6 ? C_HIT : r == 7 ? C_STILL : C_BTN;
        rightColor = value(w, k) > 0.5 ? mix(TEXT, lampColor, 0.5) : DIM;
    }
    col = mix(col, mix(DIM, leftColor, live), leftText);
    col = mix(col, mix(DIM, rightColor, live), rightText);
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
