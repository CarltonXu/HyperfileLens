import { onUnmounted, ref, watch, type Ref } from "vue";
import { gatewaysApi } from "@/api";
import type { AxiosRequestConfig } from "@/api/client";

export type RegistrationStatus = "idle" | "polling" | "registered" | "error";

export interface UseGatewayRegistrationStatusOptions {
  /**
   * 轮询间隔（毫秒）。默认 3000。
   */
  intervalMs?: number;
}

/**
 * 轮询网关详情接口，检测 gateway.status 是否变为 "active"。
 *
 * 设计要点：
 * - 用 setInterval + inFlight 守卫，避免慢响应叠加
 * - 跳过 axios 全局错误处理（client.ts），轮询期间不弹错误 Toast
 * - onUnmounted 自动清理定时器，避免弹窗关闭后继续轮询
 * - 错误时不停止轮询（按需求"无超时"）
 */
export function useGatewayRegistrationStatus(
  gatewayId: Ref<string | null | undefined>,
  options: UseGatewayRegistrationStatusOptions = {},
) {
  const { intervalMs = 3000 } = options;

  const status = ref<RegistrationStatus>("idle");

  let timer: ReturnType<typeof setInterval> | null = null;
  let inFlight = false;

  async function tick() {
    const id = gatewayId.value;
    if (!id || inFlight) return;

    inFlight = true;
    try {
      const res = await gatewaysApi.detail(id, {
        _skipGlobalErrorHandler: true,
      } as AxiosRequestConfig);
      if (res?.data?.status === "active") {
        status.value = "registered";
        stop();
      } else if (status.value === "error") {
        // 网络抖动恢复后，从 error 退回 polling。
        status.value = "polling";
      }
    } catch (e) {
      status.value = "error";
      console.warn("[useGatewayRegistrationStatus] poll failed:", e);
    } finally {
      inFlight = false;
    }
  }

  function start() {
    if (timer || !gatewayId.value) return;
    status.value = "polling";
    tick();
    timer = setInterval(tick, intervalMs);
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function reset() {
    stop();
    status.value = "idle";
  }

  // gatewayId 从无到有时自动启动（避免外部遗漏调用 start）
  watch(
    gatewayId,
    (id) => {
      if (id) {
        start();
      } else {
        stop();
      }
    },
    { immediate: true },
  );

  onUnmounted(() => {
    stop();
  });

  return {
    status,
    start,
    stop,
    reset,
  };
}
