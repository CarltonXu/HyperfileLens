<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    columnKey: string;
    label: string;
    styleValue?: Record<string, string>;
    sortable?: boolean;
    active?: boolean;
    align?: "left" | "right" | "center";
    sortIcon?: any;
    resizing?: boolean;
    sticky?: "left" | "right";
    headerClass?: string;
  }>(),
  {
    sortable: true,
    active: false,
    align: "left",
    resizing: false,
    headerClass: "",
  },
);

const emit = defineEmits<{
  sort: [key: string];
  resizeStart: [key: string, event: MouseEvent];
  resizeReset: [key: string];
}>();

function alignClass() {
  if (props.align === "right") return "justify-end text-right";
  if (props.align === "center") return "justify-center text-center";
  return "justify-start text-left";
}

function thAlignClass() {
  if (props.align === "right") return "text-right";
  if (props.align === "center") return "text-center";
  return "text-left";
}
</script>

<template>
  <th
    :style="styleValue"
    :class="[
      'relative bg-background-secondary px-4 py-3 text-xs font-medium uppercase tracking-wider text-foreground-secondary whitespace-nowrap',
      thAlignClass(),
      sticky === 'left' ? 'sticky left-0 z-10' : '',
      sticky === 'right' ? 'sticky right-0 z-10' : '',
      headerClass,
    ]"
  >
    <button
      v-if="sortable"
      type="button"
      @click="emit('sort', columnKey)"
      :class="[
        'group/sort inline-flex max-w-full items-center gap-1.5 rounded-md hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
        alignClass(),
      ]"
    >
      <span class="truncate">{{ label }}</span>
      <component
        v-if="sortIcon"
        :is="sortIcon"
        :class="[
          'h-3.5 w-3.5 flex-shrink-0 transition-colors',
          active
            ? 'text-primary'
            : 'text-foreground-muted group-hover/sort:text-foreground-secondary',
        ]"
      />
    </button>
    <div v-else :class="['flex max-w-full items-center gap-1.5', alignClass()]">
      <span class="truncate">{{ label }}</span>
    </div>
    <span
      role="separator"
      aria-orientation="vertical"
      @mousedown="emit('resizeStart', columnKey, $event)"
      @dblclick.stop="emit('resizeReset', columnKey)"
      :class="[
        'absolute right-0 top-0 h-full w-2 cursor-col-resize select-none touch-none',
        'after:absolute after:right-0 after:top-2 after:h-[calc(100%-1rem)] after:w-px after:bg-border',
        'hover:after:bg-primary',
        resizing ? 'after:bg-primary' : '',
      ]"
    />
  </th>
</template>
