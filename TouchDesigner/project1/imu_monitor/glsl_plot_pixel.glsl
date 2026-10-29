// IMU graphs: input 0 is the trail as a texture, one row per channel
// (ax ay az gx gy gz), one column per sample, oldest on the left.
// Top panel: acceleration, middle panel: rotation, bottom strip: left dark
// for the value text. uRange.x / .y = accel / gyro value at the panel edge.
uniform vec4 uRange;
layout(location = 0) out vec4 fragColor;

const float TEXT_H = 120.0;
const vec3 COLORS[3] = vec3[3](vec3(0.95, 0.35, 0.35), vec3(0.40, 0.85, 0.45), vec3(0.40, 0.60, 1.00));

float valueAt(int chan, float x, float w) {
    int n = int(uTD2DInfos[0].res.z);
    float s = clamp(x / w, 0.0, 1.0) * float(n - 1);
    int i = int(floor(s));
    float a = texelFetch(sTD2DInputs[0], ivec2(i, chan), 0).r;
    float b = texelFetch(sTD2DInputs[0], ivec2(min(i + 1, n - 1), chan), 0).r;
    return mix(a, b, fract(s));
}

// pixel y of a value inside a panel starting at y0 with height h
float toY(float v, float range, float y0, float h) {
    return y0 + h * (0.5 + 0.45 * clamp(v / range, -1.0, 1.0));
}

vec3 panel(vec2 p, float w, float y0, float h, int firstChan, float range, vec3 col) {
    if (p.y < y0 || p.y >= y0 + h) return col;
    col = vec3(0.05);
    float mid = y0 + 0.5 * h;
    float edge = 0.45 * h;
    float row = floor(p.y);
    if (row == floor(mid + 0.5 * edge) || row == floor(mid - 0.5 * edge)) col = vec3(0.10);  // +-half range
    if (row == floor(mid + edge) || row == floor(mid - edge)) col = vec3(0.16);              // +-range
    if (row == floor(mid)) col = vec3(0.30);                                                 // zero
    for (int c = 0; c < 3; c++) {
        float y = toY(valueAt(firstChan + c, p.x, w), range, y0, h);
        float slope = toY(valueAt(firstChan + c, p.x + 1.0, w), range, y0, h) - toY(valueAt(firstChan + c, p.x - 1.0, w), range, y0, h);
        float d = abs(p.y - y) / sqrt(1.0 + 0.25 * slope * slope);
        col = mix(col, COLORS[c], smoothstep(1.6, 0.6, d));
    }
    if (p.y < y0 + 1.0) col = vec3(0.25);                                         // panel separator
    return col;
}

void main() {
    vec2 res = uTDOutputInfo.res.zw;
    vec2 p = vUV.st * res;
    float h = 0.5 * (res.y - TEXT_H);
    vec3 col = vec3(0.08);
    if (TD_NUM_2D_INPUTS > 0 && uTD2DInfos[0].res.w >= 6.0) {
        col = panel(p, res.x, TEXT_H + h, h, 0, uRange.x, col);
        col = panel(p, res.x, TEXT_H, h, 3, uRange.y, col);
    }
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
