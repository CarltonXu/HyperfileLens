<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";

export interface ProductTourStep {
  selector: string;
  title: string;
  description: string;
  route?: string;
  actionLabel?: string;
  onAction?: () => void;
}

const props = defineProps<{
  steps: ProductTourStep[];
  active: boolean;
}>();

const emit = defineEmits<{
  finish: [];
  skip: [];
}>();

const { locale } = useI18n();
const router = useRouter();
const route = useRoute();

const currentIndex = ref(0);
const targetRect = ref<DOMRect | null>(null);
const tooltipRect = ref({ left: 24, top: 24 });
const viewport = ref({ width: window.innerWidth, height: window.innerHeight });
let positionRequestId = 0;

const currentStep = computed(() => props.steps[currentIndex.value]);
const isLastStep = computed(() => currentIndex.value >= props.steps.length - 1);

const copy = computed(() => {
  const zh = locale.value === "zh-CN";
  return {
    next: zh ? "下一步" : "Next",
    previous: zh ? "上一步" : "Previous",
    skip: zh ? "跳过" : "Skip",
    finish: zh ? "完成" : "Finish",
    step: zh ? "步骤" : "Step",
  };
});

async function waitForTarget(selector: string) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const target = document.querySelector(selector);
    if (target instanceof HTMLElement) {
      return target;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return null;
}

async function updatePosition() {
  const requestId = ++positionRequestId;
  viewport.value = { width: window.innerWidth, height: window.innerHeight };
  const step = currentStep.value;
  if (!props.active || !step) return;

  if (step.route && route.path !== step.route) {
    await router.push(step.route);
    await nextTick();
  }

  window.dispatchEvent(
    new CustomEvent("hfl:prepare-tour-step", { detail: step }),
  );
  await nextTick();

  const target = await waitForTarget(step.selector);
  if (requestId !== positionRequestId) return;

  if (!target) {
    targetRect.value = null;
    tooltipRect.value = { left: 24, top: 24 };
    return;
  }

  target.scrollIntoView({
    block: "center",
    inline: "center",
    behavior: "smooth",
  });

  window.setTimeout(() => {
    if (requestId !== positionRequestId) return;
    const rect = target.getBoundingClientRect();
    targetRect.value = rect;

    const tooltipWidth = 360;
    const tooltipHeight = 190;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const gap = 16;

    let left = rect.left;
    let top = rect.bottom + gap;

    if (left + tooltipWidth > viewportWidth - gap) {
      left = viewportWidth - tooltipWidth - gap;
    }
    if (top + tooltipHeight > viewportHeight - gap) {
      top = rect.top - tooltipHeight - gap;
    }

    tooltipRect.value = {
      left: Math.max(gap, left),
      top: Math.max(gap, top),
    };
  }, 220);
}

function next() {
  if (isLastStep.value) {
    emit("finish");
    return;
  }
  currentIndex.value += 1;
}

function previous() {
  currentIndex.value = Math.max(0, currentIndex.value - 1);
}

function skip() {
  emit("skip");
}

function handleKeydown(event: KeyboardEvent) {
  if (!props.active) return;
  if (event.key === "Escape") {
    skip();
  } else if (event.key === "ArrowRight") {
    next();
  } else if (event.key === "ArrowLeft") {
    previous();
  }
}

watch(
  () => props.active,
  async (active) => {
    if (!active) return;
    currentIndex.value = 0;
    await nextTick();
    updatePosition();
  },
);

watch(currentIndex, async () => {
  await nextTick();
  updatePosition();
});

watch(
  () => route.path,
  async () => {
    if (!props.active) return;
    await nextTick();
    updatePosition();
  },
);

window.addEventListener("resize", updatePosition);
window.addEventListener("scroll", updatePosition, true);
window.addEventListener("keydown", handleKeydown);

onBeforeUnmount(() => {
  window.removeEventListener("resize", updatePosition);
  window.removeEventListener("scroll", updatePosition, true);
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <Teleport to="body">
    <div v-if="active && currentStep" class="fixed inset-0 z-[1000]">
      <template v-if="targetRect">
        <div
          class="fixed left-0 top-0 bg-slate-950/[0.62]"
          :style="{
            width: '100vw',
            height: `${Math.max(0, targetRect.top - 8)}px`,
          }"
        />
        <div
          class="fixed left-0 bg-slate-950/[0.62]"
          :style="{
            top: `${Math.max(0, targetRect.top - 8)}px`,
            width: `${Math.max(0, targetRect.left - 8)}px`,
            height: `${targetRect.height + 16}px`,
          }"
        />
        <div
          class="fixed bg-slate-950/[0.62]"
          :style="{
            left: `${targetRect.right + 8}px`,
            top: `${Math.max(0, targetRect.top - 8)}px`,
            width: `${Math.max(0, viewport.width - targetRect.right - 8)}px`,
            height: `${targetRect.height + 16}px`,
          }"
        />
        <div
          class="fixed bottom-0 left-0 bg-slate-950/[0.62]"
          :style="{
            top: `${targetRect.bottom + 8}px`,
            width: '100vw',
          }"
        />
        <div
          class="fixed rounded-xl border-2 border-violet-400 shadow-[0_0_0_4px_rgba(139,92,246,0.22),0_20px_60px_rgba(15,23,42,0.35)]"
          :style="{
            left: `${targetRect.left - 8}px`,
            top: `${targetRect.top - 8}px`,
            width: `${targetRect.width + 16}px`,
            height: `${targetRect.height + 16}px`,
          }"
        />
      </template>
      <div v-else class="fixed inset-0 bg-slate-950/[0.62]" />

      <div
        class="fixed w-[min(360px,calc(100vw-32px))] rounded-xl border border-border bg-card p-4 text-foreground shadow-2xl"
        :style="{ left: `${tooltipRect.left}px`, top: `${tooltipRect.top}px` }"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-xs font-medium uppercase text-violet-500">
              {{ copy.step }} {{ currentIndex + 1 }} / {{ steps.length }}
            </p>
            <h3 class="mt-1 text-base font-semibold">
              {{ currentStep.title }}
            </h3>
          </div>
          <button
            type="button"
            class="rounded-md px-2 py-1 text-xs text-foreground-secondary hover:bg-hover hover:text-foreground"
            @click="skip"
          >
            {{ copy.skip }}
          </button>
        </div>
        <p class="mt-3 text-sm leading-6 text-foreground-secondary">
          {{ currentStep.description }}
        </p>
        <button
          v-if="currentStep.actionLabel && currentStep.onAction"
          type="button"
          class="mt-3 text-sm font-medium text-violet-600 hover:text-violet-700 dark:text-violet-300 dark:hover:text-violet-200"
          @click="currentStep.onAction"
        >
          {{ currentStep.actionLabel }}
        </button>
        <div class="mt-4 flex items-center justify-between gap-3">
          <button
            type="button"
            class="rounded-lg border border-border px-3 py-2 text-sm text-foreground-secondary hover:bg-hover disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="currentIndex === 0"
            @click="previous"
          >
            {{ copy.previous }}
          </button>
          <button
            type="button"
            class="rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700"
            @click="next"
          >
            {{ isLastStep ? copy.finish : copy.next }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
