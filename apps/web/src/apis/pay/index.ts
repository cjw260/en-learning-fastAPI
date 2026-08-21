import { serverApi, type Response } from "..";
import type { CreatePayDto, PaymentStatus, ResultPay } from "@en/common/pay"

export const createPay = (data: CreatePayDto) => serverApi.post("/pay/create", data) as Promise<Response<ResultPay>>;

export const getPaymentStatus = (outTradeNo: string) =>
    serverApi.get(`/pay/status/${encodeURIComponent(outTradeNo)}`) as Promise<Response<PaymentStatus>>;
