# TablePick

WebページのHTMLから `<table>` 要素を抽出し、CSV/JSONで出力するCLIツールです。

注意: 現時点ではPyPI未公開です。GitHubからインストールしてください。

## 特長
- ページ内の全テーブルを抽出
- CSV / JSON（行オブジェクト配列）に出力
- 標準出力とファイル保存の両対応（テーブルごとに分割保存）

## 動作要件
- Python 3.10+

## インストール（GitHub）
リポジトリをクローンして、editable install します。

```bash
git clone https://github.com/koume-z/TablePick.git
cd tablepick
pip install -e .
```

## 使い方
最小構成（対話モード）:

```bash
python -m tablepick
```

明示的に指定して実行:

```bash
python -m tablepick --url https://example.com --format csv --stdout
```

ファイル保存（テーブルごとに分割保存）:

```bash
python -m tablepick --url https://example.com --format json --out-dir ./out --filename-base example --no-stdout
```

## CLIオプション
```
--url             対象URL（scheme必須: http/https）
--format          出力形式: csv or json（default: csv）
--out-dir         出力先ディレクトリ（任意）
--filename-base   出力ファイルのベース名（default: tablepick）
--stdout          標準出力に表示（default）
--no-stdout       標準出力を無効化
--json-indent     JSONのインデント（format=jsonのみ）
--ensure-ascii    JSONで非ASCIIをエスケープ
--timeout         HTTPタイムアウト秒
--retries         リトライ回数
--max-redirects   リダイレクト最大回数
--debug           デバッグ情報をstderrに出力
```

## 出力仕様
- CSV: ヘッダー行 + データ行
- JSON: 行オブジェクト配列（ヘッダー名をキーにする）
- 複数テーブルは順番に出力され、ファイル名には `tableXX` が付く

## 開発
依存関係とテスト実行:

```bash
pip install -r requirements.txt
pip install pytest
python -m pytest
```

## ライセンス
未定（後で記載）

