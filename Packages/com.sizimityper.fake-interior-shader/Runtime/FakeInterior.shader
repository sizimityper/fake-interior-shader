// sizimityper Fake Interior Shader
// 窓ガラス面（板ポリ）に貼るだけで、奥に部屋があるように見せるインテリアマッピングシェーダー。
// 部屋テクスチャは「窓の正面から一点透視で撮った部屋の画像」1枚（奥壁が中央、周囲に床・天井・左右の壁の台形）。
// 1マテリアル = 1部屋。ライティングは行わない Unlit シェーダー。
Shader "sizimityper/FakeInterior"
{
    Properties
    {
        [Header(Room)]
        _RoomTex ("部屋テクスチャ (一点透視・奥壁が中央)", 2D) = "white" {}
        _BackWallScale ("奥壁の大きさ (テクスチャ幅に対する比率)", Range(0.05, 0.95)) = 0.5
        _WindowSize ("窓のサイズ XY (オブジェクト空間の単位, 通常メートル)", Vector) = (1, 1, 0, 0)
        _RoomDepth ("部屋の奥行き (窓サイズと同じ単位)", Range(0.01, 20)) = 1
        _RoomColor ("部屋カラー (乗算)", Color) = (1, 1, 1, 1)
        _Brightness ("明るさ (発光強度)", Range(0, 8)) = 1
        _DepthDarken ("奥ほど暗くする", Range(0, 1)) = 0
        [Toggle(_FLIP_X)] _FlipX ("部屋を左右反転", Float) = 0

        [Header(Middle Layer)]
        [Toggle(_MIDDLE_LAYER)] _MiddleLayer ("中間レイヤーを使う (カーテン・ブラインド・家具など)", Float) = 0
        _MiddleTex ("中間レイヤー (RGBA, αで重ねる)", 2D) = "white" {}
        _MiddleDepth ("中間レイヤーの位置 (0=窓面 1=奥壁)", Range(0, 1)) = 0.1
        _MiddleColor ("中間レイヤーカラー (乗算)", Color) = (1, 1, 1, 1)

        [Header(Glass)]
        _GlassColor ("ガラスカラー (乗算)", Color) = (1, 1, 1, 1)
        _GlassTex ("ガラス汚れ・映り込み (RGBA, αで重ねる)", 2D) = "black" {}
        _GlassOpacity ("ガラス汚れの不透明度", Range(0, 1)) = 0
    }

    SubShader
    {
        // オブジェクト空間の部屋寸法を使うため、頂点を世界座標へ焼く動的バッチを禁止する。
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" "DisableBatching" = "True" }
        LOD 100

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #pragma shader_feature_local _MIDDLE_LAYER
            #pragma shader_feature_local _FLIP_X
            #pragma target 3.0

            #include "UnityCG.cginc"

            sampler2D _RoomTex;
            float4 _RoomTex_ST;
            float _BackWallScale;
            float4 _WindowSize;
            float _RoomDepth;
            half4 _RoomColor;
            half _Brightness;
            half _DepthDarken;

            sampler2D _MiddleTex;
            float4 _MiddleTex_ST;
            float _MiddleDepth;
            half4 _MiddleColor;

            half4 _GlassColor;
            sampler2D _GlassTex;
            float4 _GlassTex_ST;
            half _GlassOpacity;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 tangent : TANGENT;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                // 接線空間でのカメラ方向（頂点→カメラ, 正規化しない＝線形補間で正しく補間される）
                float3 viewTS : TEXCOORD1;
                UNITY_FOG_COORDS(2)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert (appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;

                // オブジェクト空間のカメラ方向を接線空間へ変換（X=U方向, Y=V方向, Z=法線方向）
                float3 viewOS = ObjSpaceViewDir(v.vertex);
                float3 n = normalize(v.normal);
                float3 t = normalize(v.tangent.xyz);
                // 視線も基底もオブジェクト空間。負スケールの符号を二重適用しない。
                float3 b = cross(n, t) * v.tangent.w;
                o.viewTS = float3(dot(viewOS, t), dot(viewOS, b), dot(viewOS, n));

                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            // 0 割りを避けつつ符号を保つ
            float3 SafeDir(float3 d)
            {
                float3 s = d >= 0 ? 1.0 : -1.0;
                return abs(d) < 1e-5 ? s * 1e-5 : d;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);

                float2 winUV = i.uv;
                #if defined(_FLIP_X)
                    winUV.x = 1.0 - winUV.x;
                #endif

                float2 size = max(_WindowSize.xy, 1e-4);
                float depth = max(_RoomDepth, 1e-4);

                // ---- 部屋の箱とレイの交差 ----
                // 箱: X,Y は窓の大きさ、Z は 0(窓面)〜depth(奥壁)。Z は部屋の内側方向を正とする。
                float3 v = i.viewTS;
                #if defined(_FLIP_X)
                    v.x = -v.x;
                #endif
                float3 dir = SafeDir(float3(-v.x, -v.y, max(v.z, 1e-5)));

                // 箱の中心を原点にとる
                float3 halfSize = float3(size * 0.5, depth * 0.5);
                float3 start = float3((winUV - 0.5) * size, -depth * 0.5);

                // 各軸で、進行方向側の面に当たるまでの距離。最小のものが実際に当たる面。
                float3 tAxis = (sign(dir) * halfSize - start) / dir;
                float tHit = min(min(tAxis.x, tAxis.y), tAxis.z);
                float3 hit = start + dir * tHit;

                // 奥行き率 0(窓面)〜1(奥壁)
                float zFrac = saturate((hit.z + halfSize.z) / depth);
                // 窓の枠を ±1 とした正規化座標
                float2 nrm = hit.xy / halfSize.xy;

                // ---- 一点透視テクスチャへの投影 ----
                // 奥行き率 z の点は、画像上で 1 / (1 + z * k) 倍に縮んで見える（k = 1/奥壁比率 - 1）
                float k = 1.0 / _BackWallScale - 1.0;
                float2 roomUV = nrm / (1.0 + zFrac * k) * 0.5 + 0.5;
                roomUV = roomUV * _RoomTex_ST.xy + _RoomTex_ST.zw;

                // 壁の角でUVが不連続になり、ミップが飛んで線が出るのを防ぐ。
                // 投影後の微分が窓面UVの微分より極端に大きい画素では窓面側の微分を使う。
                float2 dxR = ddx(roomUV), dyR = ddy(roomUV);
                float2 dxW = ddx(i.uv) * _RoomTex_ST.xy, dyW = ddy(i.uv) * _RoomTex_ST.xy;
                float limit = 4.0 * max(dot(dxW, dxW), dot(dyW, dyW)) + 1e-12;
                bool seam = max(dot(dxR, dxR), dot(dyR, dyR)) > limit;
                float2 gx = seam ? dxW : dxR;
                float2 gy = seam ? dyW : dyR;

                half3 col = tex2Dgrad(_RoomTex, roomUV, gx, gy).rgb * _RoomColor.rgb;
                col *= lerp(1.0, 1.0 - zFrac, _DepthDarken);

                // ---- 中間レイヤー（カーテン等）----
                #if defined(_MIDDLE_LAYER)
                {
                    float planeZ = _MiddleDepth * depth;
                    float tm = planeZ / dir.z;
                    float2 mxy = start.xy + dir.xy * tm;
                    float2 midUV = mxy / size + 0.5;
                    // 平面より手前で壁に当たっている（=平面が壁の外）なら見えない
                    float inside = (tm <= tHit) && all(abs(mxy) <= halfSize.xy) ? 1.0 : 0.0;
                    float2 midUVst = midUV * _MiddleTex_ST.xy + _MiddleTex_ST.zw;
                    // カーテン平面へ投影した実際のUVからミップの微分を求める。
                    half4 mid = tex2Dgrad(_MiddleTex, midUVst, ddx(midUVst), ddy(midUVst)) * _MiddleColor;
                    col = lerp(col, mid.rgb, mid.a * inside);
                }
                #endif

                col *= _Brightness;

                // ---- ガラス面 ----
                col *= _GlassColor.rgb;
                half4 glass = tex2D(_GlassTex, TRANSFORM_TEX(i.uv, _GlassTex));
                col = lerp(col, glass.rgb, glass.a * _GlassOpacity);

                fixed4 outCol = fixed4(col, 1.0);
                UNITY_APPLY_FOG(i.fogCoord, outCol);
                return outCol;
            }
            ENDCG
        }
    }
    Fallback Off
}
