import pandas as pd
from web3 import Web3

# --- 1. 连接节点 ---
# ⚠️⚠️⚠️ 请务必将下面的 URL 替换为你自己的 Alchemy 或 Infura URL ⚠️⚠️⚠️
#重要！
RPC_URL = '你的URL'
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print("❌ 连接失败，请检查 RPC URL 是否正确，或者 API Key 是否过期")
    exit()
else:
    print(f"✅ 连接成功，当前区块高度: {w3.eth.block_number}")

# --- 2. 目标配置：USDC/ETH Pair (Uniswap V2) ---
PAIR_ADDRESS = "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc"

# 最小化的 ABI
PAIR_ABI = '[{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount0Out","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1Out","type":"uint256"},{"indexed":true,"internalType":"address","name":"to","type":"address"}],"name":"Swap","type":"event"}]'

# 创建合约对象
contract = w3.eth.contract(address=PAIR_ADDRESS, abi=PAIR_ABI)


# --- 3. 核心逻辑：获取数据 ---
def fetch_swaps(lookback_blocks=50):
    try:
        current_block = w3.eth.block_number
        start_block = current_block - lookback_blocks

        print(f"🔍 正在抓取从 {start_block} 到 {current_block} 的数据...")

        # 🔥【关键修改点】🔥
        # Web3.py v6+ 必须使用 from_block 和 to_block (下划线命名)
        # 这里的 Swap 是事件名称
        events = contract.events.Swap.create_filter(
            from_block=start_block,
            to_block=current_block
        ).get_all_entries()

        data = []
        for event in events:
            args = event['args']

            # --- 数据清洗 ---
            # USDC (Token0) = 6 decimals
            # WETH (Token1) = 18 decimals

            # 简单的买卖判断逻辑：
            # 如果 amount1Out (ETH流出) > 0，说明池子少了ETH，用户买走了ETH -> Buy ETH
            # 如果 amount1In (ETH流入) > 0，说明池子多了ETH，用户卖掉了ETH -> Sell ETH

            if args['amount1Out'] > 0:
                action = "Buy ETH"
                # 用户买到的 ETH 数量
                eth_amount = args['amount1Out'] / 10 ** 18
                # 用户支付的 USDC 数量
                usdc_amount = args['amount0In'] / 10 ** 6
            else:
                action = "Sell ETH"
                # 用户卖出的 ETH 数量
                eth_amount = args['amount1In'] / 10 ** 18
                # 用户得到的 USDC 数量
                usdc_amount = args['amount0Out'] / 10 ** 6

            # 计算价格 (USDC / ETH)
            # 防止除以 0 的情况 (虽然在 Swap 事件中极少见)
            price = (usdc_amount / eth_amount) if eth_amount > 0 else 0

            data.append({
                'tx_hash': event['transactionHash'].hex(),
                'block': event['blockNumber'],
                'action': action,
                'eth_amount': eth_amount,
                'usdc_amount': usdc_amount,
                'price': price,
                'sender': args['sender']
            })

        return pd.DataFrame(data)

    except Exception as e:
        print(f"❌ 数据抓取发生错误: {e}")
        # 返回空 DataFrame 防止程序崩溃
        return pd.DataFrame()


# 测试运行
if __name__ == "__main__":
    df = fetch_swaps(20)  # 测试抓取过去 20 个区块
    if not df.empty:
        print(df.head())
        print(f"🎉 成功抓取 {len(df)} 笔交易")
    else:
        print("⚠️ 未抓取到数据或发生错误")
