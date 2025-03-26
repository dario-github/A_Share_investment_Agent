from typing import List, Dict

def get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        try:
            # 首先尝试从东方财富获取
            try:
                df = ak.stock_individual_info_em(symbol=stock_code)
                if not df.empty and '股票简称' in df['item'].values:
                    return df[df['item'] == '股票简称']['value'].iloc[0]
            except Exception as e:
                logger.warning(f"从东方财富获取股票名称失败: {str(e)}")

            # 如果东方财富失败，尝试从雪球获取
            try:
                # 转换股票代码格式
                market = 'SH' if stock_code.startswith('6') else 'SZ'
                xq_code = f"{market}{stock_code}"
                df = ak.stock_individual_basic_info_xq(symbol=xq_code)
                if not df.empty and 'org_short_name_cn' in df['item'].values:
                    return df[df['item'] == 'org_short_name_cn']['value'].iloc[0]
            except Exception as e:
                logger.warning(f"从雪球获取股票名称失败: {str(e)}")

            # 如果都失败了，返回股票代码
            logger.warning(f"无法获取股票 {stock_code} 的名称，使用代码代替")
            return stock_code

        except Exception as e:
            logger.error(f"获取股票名称时发生错误: {str(e)}")
            return stock_code

def get_stock_list(self) -> List[Dict[str, str]]:
        """获取股票列表"""
        try:
            # 获取A股股票列表
            df = ak.stock_info_a_code_name()
            if df.empty:
                logger.warning("获取到的股票列表为空")
                return []

            # 转换为所需格式
            stock_list = []
            for _, row in df.iterrows():
                stock_code = row['code']
                stock_name = row['name']
                stock_list.append({
                    'code': stock_code,
                    'name': stock_name
                })

            logger.info(f"成功获取 {len(stock_list)} 只股票信息")
            return stock_list

        except Exception as e:
            logger.error(f"获取股票列表时发生错误: {str(e)}")
            # 返回一个基础的股票代码列表作为备用
            return [{'code': f"{i:06d}", 'name': f"{i:06d}"} for i in range(600000, 600001)]