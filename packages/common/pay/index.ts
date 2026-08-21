export interface CreatePayDto {
    subject: string; //订单标题
    body: string; //附加信息 可以自定义内容
    total_amount: string; //订单金额
    courseId: string; //课程ID
}

export interface ResultPay {
    payUrl: string; //支付URL
    timeExpire: number; //过期时间
    outTradeNo?: string; // FastAPI 返回；旧 NestJS 可从 payUrl 兼容解析
}

export interface PaymentStatus {
    outTradeNo: string;
    tradeStatus: string;
    isPurchased: boolean;
}
