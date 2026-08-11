# -*- coding: utf-8 -*-
"""
模拟知识库数据生成器
生成 500+ 条 FAQ 知识库条目，包含各类预设问题。
用于演示知识库质量治理工具的检测能力。
"""

import json
import random
import hashlib
from datetime import datetime, timedelta

random.seed(42)

# ============================================================
# 基础问答模板库（按分类）
# ============================================================

FAQ_TEMPLATES = {
    "订单管理": [
        ("如何查看我的订单状态？", "您可以登录账户后，进入「我的订单」页面查看所有订单的实时状态。订单状态包括：待付款、待发货、已发货、已签收、已完成。"),
        ("订单可以修改收货地址吗？", "订单未发货前，您可以在「我的订单」中点击「修改地址」进行更改。如果订单已发货，则无法修改地址，建议您联系快递公司进行拦截。"),
        ("如何取消订单？", "在订单未发货状态下，您可以在「我的订单」页面点击「取消订单」按钮。已发货的订单不支持取消，需收到商品后申请退货。"),
        ("订单一直显示待发货怎么办？", "正常情况下，付款后48小时内会发货。如超过48小时仍未发货，请联系在线客服查询原因。"),
        ("可以合并多个订单一起发货吗？", "如果您有多个未发货的订单，可以联系客服申请合并发货。合并后运费按一个订单计算。"),
        ("订单号在哪里查看？", "登录账户后进入「我的订单」，每笔订单左侧会显示订单编号，格式为DD+12位数字。您也可以在订单确认短信中查看。"),
        ("下单后多久能发货？", "现货商品付款后48小时内发货，预售商品按页面标注的发货时间发货，定制商品按商品详情页标注的周期发货。"),
        ("订单分多个包裹发货吗？", "如果您购买的商品来自不同仓库，订单可能会拆分为多个包裹发货。您可以在订单详情中查看每个包裹的物流单号。"),
    ],
    "退换货": [
        ("七天无理由退货的条件是什么？", "商品需保持原装未拆封状态，不影响二次销售。内衣、食品、定制商品等不支持七天无理由退货。退货运费由买家承担。"),
        ("退货流程是什么？", "1. 在「我的订单」中申请退货；2. 等待客服审核通过；3. 将商品寄回指定地址；4. 仓库签收后3-5个工作日内退款到原支付账户。"),
        ("换货需要多长时间？", "换货申请审核通过后，您需将原商品寄回。仓库收到退货后1-2个工作日内寄出新商品，物流时间根据收货地址而定。"),
        ("退款多久到账？", "支付宝/微信支付：1-3个工作日到账。银行卡支付：3-7个工作日到账。具体到账时间以银行为准。"),
        ("商品有质量问题怎么处理？", "请在签收后7天内联系客服，提供商品照片和订单号。经核实后可免费退换，运费由卖家承担。"),
        ("退货时需要保留包装吗？", "是的，退货时请保留商品原包装、配件、吊牌和赠品。包装不完整可能影响退货审核。"),
        ("可以退货到门店吗？", "目前支持线上退货，暂不支持门店退货。请按系统提供的退货地址将商品寄回。"),
    ],
    "支付问题": [
        ("支持哪些支付方式？", "我们支持微信支付、支付宝、银行卡支付、花呗分期和信用卡分期。具体可用方式以下单页面显示为准。"),
        ("付款失败怎么办？", "请检查您的支付账户余额是否充足、网络是否正常。如多次尝试仍失败，建议更换支付方式或联系银行客服。"),
        ("可以使用优惠券和满减同时使用吗？", "优惠券和满减活动可以叠加使用，但每笔订单只能使用一张优惠券。系统会自动计算最优方案。"),
        ("花呗分期有手续费吗？", "花呗分期手续费根据分期数不同：3期免手续费，6期手续费率3%，12期手续费率6%。具体以支付宝页面显示为准。"),
        ("如何开具电子发票？", "下单时在发票选项中选择「电子发票」，填写抬头和税号。发票将在订单完成后24小时内发送至您的邮箱。"),
        ("支付时扣款了但订单未生成怎么办？", "如遇此情况，款项一般会在1-3个工作日内自动退回。如未退回，请联系客服并提供支付凭证截图。"),
        ("可以货到付款吗？", "部分城市和商品支持货到付款，具体以下单页面是否有该选项为准。货到付款仅支持现金支付。"),
    ],
    "物流配送": [
        ("你们用什么快递？", "我们默认使用顺丰快递，部分地区使用圆通、中通快递。偏远地区可能使用EMS。您可以在下单时选择快递类型。"),
        ("多久能送到？", "一线城市1-3天，二三线城市2-5天，偏远地区5-10天。具体时效以快递公司实际配送为准。"),
        ("快递费怎么算？", "快递费根据商品重量、体积和收货地址计算。满99元包邮（偏远地区除外）。具体运费以下单页面显示为准。"),
        ("可以指定送达时间吗？", "顺丰快递支持指定送达时间，您可以在下单时备注希望送达的时间段。其他快递暂不支持。"),
        ("如何查询物流信息？", "发货后系统会发送物流单号短信。您也可以在「我的订单」中点击「查看物流」实时追踪。"),
        ("支持海外配送吗？", "目前仅支持中国大陆地区配送，暂不支持海外配送。港澳台地区暂不支持配送。"),
        ("快递丢失怎么办？", "如快递显示签收但您未收到，请先联系快递员核实。如确认丢失，请联系客服申请补发或退款。"),
        ("可以自提吗？", "部分城市支持门店自提，下单时选择「到店自提」选项并选择门店。自提订单需在3天内取走。"),
    ],
    "商品咨询": [
        ("商品是正品吗？", "我们所有商品均来自官方渠道，保证100%正品。每件商品都带有防伪标识，您可以通过官网验证。"),
        ("商品有保质期吗？", "食品、化妆品等商品有保质期，具体以商品详情页标注为准。发货时确保剩余保质期不少于总保质期的2/3。"),
        ("商品尺寸怎么看？", "每件商品详情页都有详细的尺寸对照表。建议您根据自身情况参考尺码表选择，也可以咨询在线客服获取建议。"),
        ("商品颜色有色差吗？", "我们尽量还原商品真实颜色，但由于显示器差异，可能存在轻微色差。如对颜色有严格要求，建议到线下门店查看实物。"),
        ("可以看商品实物图吗？", "商品详情页展示了多角度实物图。如需更多角度的图片，请联系客服索取。"),
        ("商品缺货什么时候补？", "缺货商品一般7-15天内补货。您可以在商品页面点击「到货通知」，补货后系统会发送提醒。"),
        ("商品参数在哪里看？", "商品详情页的「规格参数」板块列出了所有商品参数，包括材质、尺寸、重量等。"),
    ],
    "账户安全": [
        ("忘记密码怎么办？", "在登录页面点击「忘记密码」，输入注册手机号，通过短信验证码重置密码。"),
        ("如何修改绑定的手机号？", "进入「账户设置」-「安全中心」-「修改手机号」，通过原手机号验证码验证后即可更换。"),
        ("账户被盗怎么办？", "请立即联系客服冻结账户，并提供注册信息和身份证明。核实后我们会协助您找回账户。"),
        ("如何注销账户？", "进入「账户设置」-「账户安全」-「注销账户」。注销前需确保无未完成订单和退款。注销后账户数据不可恢复。"),
        ("一个手机号可以注册多个账户吗？", "一个手机号只能注册一个账户。如需更换账户，请先注销原账户再重新注册。"),
        ("如何保护账户安全？", "建议设置复杂密码、开启二次验证、不在公共设备上登录、定期修改密码。如发现异常登录请及时联系客服。"),
    ],
    "优惠活动": [
        ("新人有什么优惠？", "新注册用户可领取新人专享优惠券包，包含满50减10、满100减30等多张优惠券，有效期7天。"),
        ("优惠券怎么使用？", "在结算页面选择「使用优惠券」，系统会自动推荐最优优惠券。每笔订单只能使用一张优惠券。"),
        ("优惠券过期了能补发吗？", "优惠券过期后无法补发，请在有效期内及时使用。建议关注后续活动获取新优惠券。"),
        ("积分有什么用？", "积分可以在积分商城兑换商品或抵扣现金（100积分=1元）。积分有效期为1年，请及时使用。"),
        ("会员等级怎么升级？", "消费金额累计达到升级标准即可自动升级。普通会员0元，银卡会员500元，金卡会员2000元，铂金会员5000元。"),
        ("双11有什么活动？", "双11期间全场满300减50，部分商品限时5折。会员可叠加专属优惠券。具体活动详情请关注首页公告。"),
    ],
    "售后服务": [
        ("保修期是多久？", "电子产品保修1年，家电保修3年（主机），配件保修3个月。具体以商品详情页保修说明为准。"),
        ("如何申请售后维修？", "在「我的订单」中找到对应订单，点击「申请售后」-「维修」，填写问题描述并上传照片。客服会在24小时内联系您。"),
        ("售后维修收费吗？", "保修期内非人为损坏免费维修。保修期外或人为损坏需收取维修费，具体费用以检测后报价为准。"),
        ("维修需要多长时间？", "一般维修周期为7-15个工作日。如需更换配件，时间可能延长。维修完成后我们会快递寄回。"),
        ("可以延长保修期吗？", "部分商品支持购买延保服务，可在下单时选择。延保费用根据商品价格和延保时长计算。"),
    ],
    "会员权益": [
        ("会员有哪些权益？", "会员享有专属折扣、优先客服、生日礼包、积分加速等权益。等级越高权益越多。"),
        ("会员等级会降级吗？", "会员等级每年1月1日根据上一年消费金额重新评定。如未达到当前等级标准，将自动降级。"),
        ("会员生日礼包是什么？", "金卡及以上会员在生日当月可领取专属礼包，包含优惠券和实物礼品。请在生日当月登录领取。"),
        ("会员积分怎么获取？", "购物消费每1元积1分，评价商品10积分，晒单20积分。不同会员等级有积分加速：银卡1.2倍，金卡1.5倍，铂金2倍。"),
    ],
    "发票相关": [
        ("可以开增值税专票吗？", "企业用户可以开具增值税专用发票，需提供企业名称、税号、地址电话、开户行及账号。发票将在订单完成后3-5个工作日内寄出。"),
        ("发票抬头写错了怎么办？", "电子发票在开具后24小时内可以联系客服修改抬头。纸质发票一旦开具无法修改，需退回重开。"),
        ("发票内容写什么？", "发票内容默认为商品明细。如需开具其他内容（如办公用品），请在下单时备注说明。"),
        ("之前订单补开发票可以吗？", "可以。请在订单完成后30天内联系客服申请补开，超期无法补开。"),
    ],
}

# ============================================================
# 问题注入器：向数据中插入各类问题条目
# ============================================================

def inject_outdated_entries(entries):
    """注入内容过时条目"""
    outdated_items = [
        {
            "category": "优惠活动",
            "question": "618大促活动有哪些优惠？",
            "answer": "2022年618大促活动：6月1日-6月20日，满200减30，满500减80。还有跨店满减每满300减50。iPhone 13系列直降500元。",
            "problem": "outdated",
            "issue_desc": "引用了2022年618活动，活动已结束且年份过时"
        },
        {
            "category": "支付问题",
            "question": "支持百度钱包支付吗？",
            "answer": "我们支持百度钱包支付。下单时在支付方式中选择百度钱包即可。百度钱包支付还可享受随机立减优惠。",
            "problem": "outdated",
            "issue_desc": "百度钱包已更名为度小满支付，且大部分电商平台已下线该支付方式"
        },
        {
            "category": "物流配送",
            "question": "疫情期间快递时效有影响吗？",
            "answer": "受疫情影响，湖北地区快递暂停发货，其他地区时效延长3-5天。具体恢复时间另行通知。",
            "problem": "outdated",
            "issue_desc": "引用疫情管控政策，已不适用于当前情况"
        },
        {
            "category": "优惠活动",
            "question": "双12有什么活动？",
            "answer": "2021年双12活动：满199减25，满399减50。部分商品限时秒杀低至3折。会员专属优惠券满500减100。",
            "problem": "outdated",
            "issue_desc": "引用2021年双12活动，信息已过时"
        },
        {
            "category": "售后服务",
            "question": "手机维修配件价格表",
            "answer": "iPhone 12屏幕维修价格：599元。iPhone 12 Pro屏幕维修价格：799元。以上价格为2021年标准。",
            "problem": "outdated",
            "issue_desc": "价格标注为2021年标准，已过时"
        },
    ]
    for item in outdated_items:
        entries.append(_make_entry(item))


def inject_contradiction_entries(entries):
    """注入条目矛盾"""
    contradiction_pairs = [
        # 矛盾对1: 退货时限
        (
            {
                "category": "退换货",
                "question": "收货后多少天内可以申请退货？",
                "answer": "签收后7天内可以申请退货。超过7天不支持退货，如有质量问题请联系客服特殊处理。",
            },
            {
                "category": "退换货",
                "question": "商品签收后还能退货吗？多久内可以退？",
                "answer": "签收后15天内可以申请无理由退货。质量问题在签收后30天内均可申请售后。",
            }
        ),
        # 矛盾对2: 包邮门槛
        (
            {
                "category": "物流配送",
                "question": "包邮的门槛是多少？",
                "answer": "订单满99元即可享受包邮服务，偏远地区（新疆、西藏、青海）需满199元包邮。",
            },
            {
                "category": "物流配送",
                "question": "什么情况下免运费？",
                "answer": "全场满79元包邮，不限地区。会员用户无论金额多少均免运费。",
            }
        ),
        # 矛盾对3: 退款到账时间
        (
            {
                "category": "退换货",
                "question": "退款大概多久能到账？",
                "answer": "支付宝和微信支付1-3个工作日到账，银行卡3-7个工作日到账。",
            },
            {
                "category": "退换货",
                "question": "退款到账时间要多久？",
                "answer": "退款即时到账。申请退款后款项会立即退回原支付账户。",
            }
        ),
    ]
    for pair in contradiction_pairs:
        for item in pair:
            item["problem"] = "contradiction"
            item["issue_desc"] = "与其他条目存在矛盾"
            entries.append(_make_entry(item))


def inject_duplicate_entries(entries):
    """注入内容重复条目"""
    duplicate_items = [
        {
            "category": "订单管理",
            "question": "怎样查看订单状态？",
            "answer": "您可以登录账户后，进入「我的订单」页面查看所有订单的实时状态。订单状态包括：待付款、待发货、已发货、已签收、已完成。",
            "problem": "duplicate",
            "issue_desc": "与「如何查看我的订单状态？」内容高度重复"
        },
        {
            "category": "订单管理",
            "question": "怎么查我的订单？",
            "answer": "登录账户后进入「我的订单」页面，即可查看所有订单的实时状态，包括待付款、待发货、已发货、已签收、已完成等状态。",
            "problem": "duplicate",
            "issue_desc": "与「如何查看我的订单状态？」内容高度重复"
        },
        {
            "category": "退换货",
            "question": "退货的流程是怎样的？",
            "answer": "1. 在「我的订单」中申请退货；2. 等待客服审核通过；3. 将商品寄回指定地址；4. 仓库签收后3-5个工作日内退款到原支付账户。",
            "problem": "duplicate",
            "issue_desc": "与「退货流程是什么？」内容高度重复"
        },
        {
            "category": "支付问题",
            "question": "有哪些支付方式可以用？",
            "answer": "我们支持微信支付、支付宝、银行卡支付、花呗分期和信用卡分期。具体可用方式以下单页面显示为准。",
            "problem": "duplicate",
            "issue_desc": "与「支持哪些支付方式？」内容高度重复"
        },
        {
            "category": "物流配送",
            "question": "快递一般用什么？",
            "answer": "我们默认使用顺丰快递，部分地区使用圆通、中通快递。偏远地区可能使用EMS。您可以在下单时选择快递类型。",
            "problem": "duplicate",
            "issue_desc": "与「你们用什么快递？」内容高度重复"
        },
    ]
    for item in duplicate_items:
        entries.append(_make_entry(item))


def inject_incomplete_entries(entries):
    """注入回答不完整条目"""
    incomplete_items = [
        {
            "category": "退换货",
            "question": "退货运费由谁承担？",
            "answer": "七天无理由退货的运费由买家承担。",
            "problem": "incomplete",
            "issue_desc": "仅说明无理由退货运费，未说明质量问题退货运费、换货运费等情况"
        },
        {
            "category": "支付问题",
            "question": "花呗分期怎么操作？",
            "answer": "在结算页面选择花呗分期即可。",
            "problem": "incomplete",
            "issue_desc": "未说明分期手续费率、支持的商品范围、最低金额要求等关键信息"
        },
        {
            "category": "商品咨询",
            "question": "商品不支持配送到我所在的地方怎么办？",
            "answer": "建议您更换收货地址试试。",
            "problem": "incomplete",
            "issue_desc": "回答过于简短，未提供具体解决方案（如转运、联系客服等）"
        },
        {
            "category": "售后服务",
            "question": "保修期内维修要带什么？",
            "answer": "带上商品就可以了。",
            "problem": "incomplete",
            "issue_desc": "未说明需携带购买凭证、保修卡、订单号等必要信息"
        },
    ]
    for item in incomplete_items:
        entries.append(_make_entry(item))


def inject_format_issue_entries(entries):
    """注入格式不规范条目"""
    format_items = [
        {
            "category": "商品咨询",
            "question": "商品材质是什么？",
            "answer": "材质：纯棉  100%    克重：180g\n\n\n\n尺寸：S/M/L/XL/XXL\n颜色：黑色 白色 灰色（注意：实际颜色可能因显示器不同而有所差异，请以实物为准）\n\n\n洗涤建议：30度以下水温 不可漂白  不可机洗   低温熨烫",
            "problem": "format_issue",
            "issue_desc": "多余换行符、不一致的间距，格式混乱难以阅读"
        },
        {
            "category": "订单管理",
            "question": "订单有哪些状态？",
            "answer": "订单状态：待付款->待发货->已发货->已签收->已完成也可在已发货前取消订单取消后不可恢复特殊状态：退款中/退款完成/已关闭",
            "problem": "format_issue",
            "issue_desc": "缺少换行和标点，内容堆砌无法阅读"
        },
        {
            "category": "会员权益",
            "question": "不同会员等级的折扣是多少？",
            "answer": "普通会员：无折扣【银卡会员：95折】{金卡会员：9折}「铂金会员：85折」※折扣不与其他优惠叠加※",
            "problem": "format_issue",
            "issue_desc": "括号样式不统一，格式混乱"
        },
        {
            "category": "物流配送",
            "question": "各地区的配送时效是多久？",
            "answer": "北京上海广州深圳：1-2天 / 杭州/南京/成都/武汉：2-3天|其他省会城市：3-4天\\偏远地区：5-10天 *偏远地区含新疆/西藏/青海/内蒙古",
            "problem": "format_issue",
            "issue_desc": "分隔符不一致（/ | \\ *），格式混乱"
        },
    ]
    for item in format_items:
        entries.append(_make_entry(item))


def inject_qa_mismatch_entries(entries):
    """注入问答不匹配条目"""
    mismatch_items = [
        {
            "category": "支付问题",
            "question": "怎么修改支付密码？",
            "answer": "您可以在账户设置中修改登录密码，点击「安全中心」-「修改密码」，通过短信验证码验证后即可修改。",
            "problem": "qa_mismatch",
            "issue_desc": "问的是支付密码，答的是登录密码修改方法"
        },
        {
            "category": "退换货",
            "question": "退货运费怎么算？",
            "answer": "我们支持微信支付、支付宝、银行卡等多种支付方式，您可以在结算页面选择。",
            "problem": "qa_mismatch",
            "issue_desc": "问的是退货运费，答的是支付方式"
        },
        {
            "category": "物流配送",
            "question": "快递可以送到乡镇吗？",
            "answer": "顺丰快递的客服电话是95338，圆通客服电话是95554。您可以联系快递公司查询具体配送范围。",
            "problem": "qa_mismatch",
            "issue_desc": "问的是能否送到乡镇，答的是快递客服电话"
        },
        {
            "category": "商品咨询",
            "question": "这个商品支持七天无理由退货吗？",
            "answer": "该商品采用优质材料制作，经过严格的质量检测，品质有保障。如有任何问题请联系客服。",
            "problem": "qa_mismatch",
            "issue_desc": "问的是退货政策，答的是商品品质介绍"
        },
    ]
    for item in mismatch_items:
        entries.append(_make_entry(item))


def inject_vague_entries(entries):
    """注入信息模糊条目"""
    vague_items = [
        {
            "category": "商品咨询",
            "question": "这个商品质量怎么样？",
            "answer": "质量挺好的，您可以放心购买。",
            "problem": "vague",
            "issue_desc": "回答过于模糊，未提供具体质量指标、材质说明等有价值信息"
        },
        {
            "category": "物流配送",
            "question": "快递大概什么时候到？",
            "answer": "快的话几天就到了，具体看快递公司的情况。",
            "problem": "vague",
            "issue_desc": "回答模糊，未给出具体的时效范围"
        },
        {
            "category": "售后服务",
            "question": "维修费用大概多少？",
            "answer": "费用不一定，看具体什么问题。您可以咨询客服了解详情。",
            "problem": "vague",
            "issue_desc": "回答模糊，未提供任何费用参考范围"
        },
        {
            "category": "优惠活动",
            "question": "最近有什么优惠活动？",
            "answer": "最近活动很多，您可以关注一下我们的页面。",
            "problem": "vague",
            "issue_desc": "回答空洞，未提供任何具体活动信息"
        },
    ]
    for item in vague_items:
        entries.append(_make_entry(item))


def inject_dead_link_entries(entries):
    """注入指向性链接失效条目"""
    dead_link_items = [
        {
            "category": "商品咨询",
            "question": "在哪里可以查看商品的详细参数？",
            "answer": "请访问 http://www.example.com/product/specs 查看详细参数。或者参考 http://192.168.1.100:8080/spec 页面。",
            "problem": "dead_link",
            "issue_desc": "包含可能失效的链接，内网地址不适合外部用户访问"
        },
        {
            "category": "售后服务",
            "question": "售后政策在哪里可以看？",
            "answer": "详细售后政策请参考：http://www.old-domain.com/policy/after-sales 。如有疑问请联系客服。",
            "problem": "dead_link",
            "issue_desc": "链接指向旧域名，可能已失效"
        },
        {
            "category": "会员权益",
            "question": "会员规则在哪里查看？",
            "answer": "会员完整规则请查看：https://test.internal.site/membership/rules 。您也可以在APP「我的-会员中心」查看。",
            "problem": "dead_link",
            "issue_desc": "链接指向内部测试地址，外部用户无法访问"
        },
    ]
    for item in dead_link_items:
        entries.append(_make_entry(item))


def _make_entry(item):
    """创建一条FAQ条目"""
    now = datetime.now()
    # 随机生成创建时间（过去1年内）
    days_ago = random.randint(0, 365)
    created = now - timedelta(days=days_ago)
    
    entry = {
        "id": "",
        "category": item["category"],
        "question": item["question"],
        "answer": item["answer"],
        "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": created.strftime("%Y-%m-%d %H:%M:%S"),
        "view_count": random.randint(10, 5000),
        "status": "published",
    }
    
    # 如果有预设问题，记录为元数据（不直接暴露给检测工具，用于后续验证）
    if "problem" in item:
        entry["_ground_truth"] = {
            "problem_type": item["problem"],
            "issue_desc": item.get("issue_desc", "")
        }
    
    return entry


def generate_kb_data():
    """生成完整的知识库数据"""
    entries = []
    
    # 1. 从模板生成正常条目（每个模板生成多个变体）
    for category, templates in FAQ_TEMPLATES.items():
        for q, a in templates:
            entry = {
                "category": category,
                "question": q,
                "answer": a,
                "created_at": "",
                "updated_at": "",
                "view_count": random.randint(10, 5000),
                "status": "published",
            }
            now = datetime.now()
            days_ago = random.randint(0, 365)
            created = now - timedelta(days=days_ago)
            entry["created_at"] = created.strftime("%Y-%m-%d %H:%M:%S")
            entry["updated_at"] = created.strftime("%Y-%m-%d %H:%M:%S")
            entries.append(entry)
    
    # 2. 通过变体扩充到500+条
    # 生成问题变体（同义不同表述，但答案一致）
    variation_prefixes = ["请问", "您好，", "咨询一下，", "我想了解，", ""]
    variation_suffixes = ["？", "呢？", "啊？", "？谢谢", ""]
    
    base_count = len(entries)
    target_count = 520
    category_list = list(FAQ_TEMPLATES.keys())
    
    while len(entries) < target_count:
        cat = random.choice(category_list)
        templates = FAQ_TEMPLATES[cat]
        q, a = random.choice(templates)
        
        # 生成变体问题
        prefix = random.choice(variation_prefixes)
        suffix = random.choice(variation_suffixes)
        # 去掉原有问号后添加变体后缀
        base_q = q.rstrip("？?")
        new_q = f"{prefix}{base_q}{suffix}"
        
        # 避免完全重复
        existing_qs = [e["question"] for e in entries]
        if new_q in existing_qs:
            continue
        
        now = datetime.now()
        days_ago = random.randint(0, 365)
        created = now - timedelta(days=days_ago)
        
        entries.append({
            "category": cat,
            "question": new_q,
            "answer": a,
            "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "view_count": random.randint(10, 5000),
            "status": "published",
        })
    
    # 3. 注入各类问题条目
    inject_outdated_entries(entries)
    inject_contradiction_entries(entries)
    inject_duplicate_entries(entries)
    inject_incomplete_entries(entries)
    inject_format_issue_entries(entries)
    inject_qa_mismatch_entries(entries)
    inject_vague_entries(entries)
    inject_dead_link_entries(entries)
    
    # 4. 分配ID并打乱顺序
    random.shuffle(entries)
    for i, entry in enumerate(entries):
        entry["id"] = f"KB_{i+1:04d}"
    
    return entries


if __name__ == "__main__":
    data = generate_kb_data()
    
    output_path = "data/kb_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 统计
    total = len(data)
    problems = sum(1 for e in data if "_ground_truth" in e)
    categories = {}
    for e in data:
        cat = e["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"生成完成！")
    print(f"总条目数: {total}")
    print(f"预设问题条目: {problems}")
    print(f"正常条目: {total - problems}")
    print(f"\n分类分布:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}条")
    
    # 统计问题类型
    problem_types = {}
    for e in data:
        if "_ground_truth" in e:
            pt = e["_ground_truth"]["problem_type"]
            problem_types[pt] = problem_types.get(pt, 0) + 1
    
    print(f"\n预设问题类型分布:")
    for pt, count in sorted(problem_types.items(), key=lambda x: -x[1]):
        print(f"  {pt}: {count}条")
    
    print(f"\n数据已保存至: {output_path}")
