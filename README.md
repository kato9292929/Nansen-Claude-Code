# Nansen × Hyperliquid Copy-Trade Bot

NansenのスマートマネーデータをリアルタイムでモニタリングしてHyperliquid上で自動コピートレードを実行するPythonボットです。

---

## 概要

1. **トレーダー発掘 (Discovery)** — NansenのPerp PnLリーダーボードから高勝率・高PnLのウォレットを自動スコアリングして追跡対象を選定
2. **ライブ監視 (Monitor)** — `smart-money.perp-trades` フィードを定期ポーリングし、追跡ウォレットの新規トレードを即座に検出
3. **コピー実行 (Execute)** — 比例サイズ計算・リスクキャップをかけたうえでHyperliquid SDKを通じてIOC指値注文を発注
4. **リスク管理 (Risk)** — ドローダウン閾値超過のトレーダーを自動除外、総ポジション上限を常時チェック

---

## 構成

```
.
├── main.py              # エントリーポイント
├── config.yaml          # 設定ファイル
├── requirements.txt
└── bot/
    ├── bot.py           # メインループ・コピートレードロジック
    ├── discovery.py     # トレーダー発掘・スコアリング
    ├── nansen.py        # Nansen MCP HTTPクライアント
    └── trader.py        # Hyperliquid注文実行ラッパー
```

---

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
# .env ファイルを作成（絶対にコミットしないこと）
echo "HL_PRIVATE_KEY=0xYOUR_PRIVATE_KEY" > .env
```

または環境変数を直接エクスポート:

```bash
export HL_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
```

### 3. config.yaml の編集

```yaml
nansen:
  api_key: "YOUR_NANSEN_API_KEY"

hyperliquid:
  private_key: "${HL_PRIVATE_KEY}"  # 環境変数から読み込み
  testnet: false                     # テスト時は true に変更
```

---

## 設定リファレンス

### `copy_trading`

| キー | デフォルト | 説明 |
|---|---|---|
| `allocation_ratio` | `0.3` | 口座残高のうちコピートレードへ割り当てる割合 (0〜1) |
| `max_traders` | `5` | 同時追跡するウォレット数の上限 |
| `max_leverage` | `5` | コピートレードに適用するレバレッジ上限 |
| `min_trade_usd` | `20.0` | コピーする最小トレードサイズ (USD) |
| `max_trade_usd` | `500.0` | コピーする最大トレードサイズ (USD) |
| `poll_interval` | `30` | ライブフィードのポーリング間隔 (秒) |

### `discovery`

| キー | デフォルト | 説明 |
|---|---|---|
| `symbols` | `["BTC","ETH","SOL",...]` | スキャン対象のHyperliquid Perpシンボル |
| `days` | `7` | リーダーボードの集計期間 (日) |
| `min_win_rate` | `0.60` | 採用最低勝率 (0〜1) |
| `min_trades` | `10` | 採用最低トレード数 |
| `min_pnl_usd` | `1000.0` | 採用最低PnL (USD) |
| `rediscover_interval` | `3600` | 発掘処理の再実行間隔 (秒) |
| `smart_money_labels` | `["Fund", ...]` | 監視対象のNansenスマートマネーラベル |

### `risk`

| キー | デフォルト | 説明 |
|---|---|---|
| `max_total_position_usd` | `5000.0` | コピートレード総ポジションの上限 (USD) |
| `max_trader_drawdown_pct` | `30.0` | 追跡開始後のドローダウンが本値(%)を超えたらトレーダーを除外 |

---

## 起動

```bash
# デフォルト設定で起動
python main.py

# 設定ファイルを指定して起動
python main.py --config config.yaml
```

ログはコンソールと `copytrade.log` に同時出力されます。

---

## トレーダースコアリング

発掘されたトレーダーは以下の複合スコアで順位付けされます。

```
スコア = log(PnL) × 0.4
       + 勝率(%) × 0.3
       + ROI(%) × 0.2
       + 信頼度(トレード数/30 を最大1.0) × 0.1
```

---

## 注意事項

> **⚠️ 本ボットは実資金を操作します。テストネットでの動作確認を強く推奨します。**

- `config.yaml` および `.env` に秘密鍵・APIキーを記載した場合、絶対にGitにコミットしないでください。
- `.gitignore` により `*.env`・`private_key.txt`・`state.json` は除外設定済みです。
- コピートレードは元のトレーダーの利益を保証するものではありません。

---

## 必要要件

- Python 3.9+
- Nansen API キー
- Hyperliquid ウォレット秘密鍵

---

## ライセンス

本リポジトリのライセンスは各自のリポジトリ設定に従ってください。
