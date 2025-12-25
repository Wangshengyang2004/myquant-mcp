"""
Conversation title generation utility.

Generates concise titles from first user message by extracting
stock codes, intent keywords, or meaningful phrases.
"""
import re


def generate_conversation_title(message: str) -> str:
    """Generate a concise title for a conversation from the first message.

    Extracts key information like stock codes, analysis types, etc.
    Falls back to truncation if no clear pattern is found.
    """
    # Remove common prefixes
    message = message.strip()
    for prefix in ["分析", "请分析", "帮我分析", "我想了解", "获取", "查询", "看看", "帮我看看", "帮我"]:
        if message.startswith(prefix):
            message = message[len(prefix):].strip()
            break

    # Try to extract stock codes (e.g., SHSE.600000, SZSE.000001)
    stock_pattern = r'[A-Z]+\.?\d{6}'
    stocks = re.findall(stock_pattern, message)
    if stocks:
        stock_str = ", ".join(stocks[:3])  # Max 3 stocks
        # Look for action keywords
        actions = {
            "基本面": "基本面分析",
            "财务": "财务分析",
            "技术": "技术分析",
            "行情": "行情查询",
            "估值": "估值分析",
            "资金": "资金流向",
            "历史": "历史数据",
            "对比": "对比分析",
            "industry": "行业分析",
            "指数": "指数分析",
        }
        for keyword, title in actions.items():
            if keyword in message:
                return f"{stock_str} - {title}"
        return f"{stock_str} - 分析"

    # Try to detect intent from keywords (order matters - more specific first)
    intent_patterns = [
        (r'(风险|回撤|波动).*(分析|评估)', '风险评估'),
        (r'(评估|分析).*(风险|回撤|波动)', '风险评估'),
        (r'(持仓|仓位|组合).*(分析|建议)', '持仓分析'),
        (r'(银行|股票|基金).*(估值|分析)', '股票估值'),
        (r'(A股|股市|大盘|市场).*(整体|今天|最近|表现)', 'A股市场概览'),
        (r'(行业|板块).*(分析|对比|表现)', '行业分析'),
        (r'(投资|交易)?.*策略.*(建议|分析)', '投资策略'),
    ]

    for pattern, title in intent_patterns:
        if re.search(pattern, message):
            return title

    # Extract key phrases (2-4 word chunks)
    # Filter out common stop words
    stop_words = {"的", "了", "是", "在", "和", "与", "或", "但是", "然后", "一下", "我", "你", "我们", "主要", "看看"}
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', message)
    meaningful_words = [w for w in words if w not in stop_words]

    if len(meaningful_words) >= 2:
        # Take first 2-3 meaningful words
        title = " ".join(meaningful_words[:3])
        if len(title) > 20:
            title = title[:20] + "..."
        return title
    elif len(meaningful_words) == 1:
        return meaningful_words[0]

    # Fallback: truncate to 30 chars
    return message[:30] + ("..." if len(message) > 30 else "")


# Test the title generator
if __name__ == "__main__":
    test_messages = [
        "分析SHSE.600000的基本面",
        "获取SHSE.600000和SZSE.000001的历史数据并对比",
        "今天A股表现怎么样",
        "帮我看看浦发银行的估值情况",
        "评估一下我的持仓风险，主要持有银行股",
        "Calculate the moving average for AAPL stock",
    ]

    for msg in test_messages:
        print(f"'{msg}' -> '{generate_conversation_title(msg)}'")
