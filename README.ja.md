<p align="center"><img src="https://raw.githubusercontent.com/QIangIQ/MMD-bone-SDK/main/assets/icon.png" width="96" alt="MMDボーンツール アイコン"></p>

<h1 align="center">MMDボーンツール (MMD Bone Tools)</h1>

<p align="center"><b>MMDモデル・モーションのボーン名を日本語から英語へ自動翻訳し、Blender・Unity・VRM・Mixamo のボーン名へ変換、VMDモーションを別のモデルへリターゲットする無料ツールです。</b></p>

**ダウンロード:** [Windows版アプリ（インストール不要）](https://github.com/QIangIQ/MMD-bone-SDK/releases/latest) ·
`pip install mmd-bone-tools` · [Webサイト](https://qiangiq.github.io/MMD-bone-SDK/ja/) · [English](https://github.com/QIangIQ/MMD-bone-SDK#readme)

![MMDボーンツールの画面](https://raw.githubusercontent.com/QIangIQ/MMD-bone-SDK/main/assets/screenshot.png)

## できること

- **ボーン名の英語化**: PMX / PMD / VMD のボーン名・モーフ名・材質名・表示枠・剛体・ジョイント名を英語に翻訳します。
  準標準ボーンは定番の英語名（`左腕` → `arm_L`、`左足ＩＫ` → `leg IK_L`）、髪・スカート・アクセサリーなどは単語ごとに翻訳します（`右スカート前２` → `skirt_front2_R`）。
- **命名規則の変換**: 日本語MMD、英語MMD、Blender（`arm.L`）、Unity Humanoid（`LeftUpperArm`）、VRM 1.0（`leftUpperArm`）、Mixamo（`mixamorig:LeftArm`）の間で、準標準ボーン110本を相互変換します。
- **モーションのリターゲット**: 日本語ボーン名のVMDを英語名のモデルへ、またはその逆へ合わせます。元モデルを指定すると、Aポーズ⇔Tポーズなど初期姿勢の違いを補正し、足の長さに合わせて移動量を調整します。
- **文字化けしないzip展開**: 日本語ファイル名（Shift-JIS）のzipを正しく展開します。
- **フォルダ一括処理**: ダウンロードフォルダ内のモデル・モーションをまとめて翻訳します。
- VMDのボーン名は15バイトまでという制限に合わせて、長い英語名は自動で短縮します（モデルとモーションで同じ規則）。

## 使い方（アプリ）

1. [最新リリース](https://github.com/QIangIQ/MMD-bone-SDK/releases/latest) から `MMDBoneTools-…-windows-x64.zip` をダウンロードして展開します。
2. `MMDBoneTools.exe` を起動します（ファイルをexeにドラッグ＆ドロップしても読み込めます）。
3. 「翻訳」タブでファイルやフォルダを追加し、「翻訳する」を押します。

※ コード署名がないため、Windows SmartScreen の警告が出る場合があります。「詳細情報」→「実行」を選んでください。

## 使い方（コマンド）

```sh
mmdbt translate モデル.pmx            # 英語名の欄を埋める（日本語名はそのまま）
mmdbt translate モデル.pmx --rename   # ボーン名そのものを英語にする
mmdbt translate ダンス.vmd            # モーションのボーン名を英語に
mmdbt retarget ダンス.vmd --model 英語モデル.pmx
mmdbt convert モデル.pmx --to unity   # Unity Humanoid の名前に
mmdbt lookup 上半身2                  # 各命名規則での名前を表示
mmdbt unpack ダウンロード.zip         # 文字化けせずに展開
mmdbt batch ダウンロードフォルダ       # まとめて翻訳
```

## よくある質問

**モーションを読み込んでもモデルが動きません。**
MMDはボーン名でモーションを適用します。モーションが日本語名（`左腕`）、モデルが英語名（`arm_L`）だと動きません。`mmdbt retarget` でモーションのボーン名をモデルに合わせてください。

**センター・上半身・下半身・足ＩＫの英語名は？**
`center`、`upper body`、`lower body`、`leg IK_L` / `leg IK_R` です。`mmdbt table` で全ボーンの対応表を表示できます。

**名前以外も変わりますか？**
変わりません。名前以外のデータはバイト単位でそのまま保存されます（元モデルを指定したリターゲットでは補正したキーフレームのみ変わります）。

## ライセンス

MIT ライセンスです。PMX / PMD / VMD の公開仕様と、Unity・VRM・Mixamo の公開ボーン一覧をもとに独自に作成しています。変換したモデルやモーションは元データの利用規約に従ってください。

**キーワード:** MMD, MikuMikuDance, ミクミクダンス, PMX, PMD, VMD, PMXエディタ, ボーン名, 英語化, 翻訳, 日本語→英語, リターゲット, モーション変換, Aポーズ, Tポーズ, Blender, mmd_tools, Unity, VRM, VRChat, Mixamo
