<script setup lang="ts">
import type {
  CaptchaAnswer,
  CaptchaChallenge,
  CaptchaPoint,
} from '../../services/captcha/schema';

import { computed, ref } from 'vue';

import { PointSelectionCaptcha } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { useWindowSize } from '@vueuse/core';
import { ElSlider } from 'element-plus';

import { toOriginalPoint } from '../../services/captcha/schema';

const props = defineProps<{
  challenge: Extract<
    CaptchaChallenge,
    { provider: 'block_puzzle' | 'click_word' }
  >;
  busy: boolean;
}>();
const emit = defineEmits<{ answer: [answer: CaptchaAnswer]; refresh: [] }>();
const { width: windowWidth } = useWindowSize();
const width = computed(() =>
  Math.min(320, Math.max(1, windowWidth.value - 64)),
);
const x = ref(0);
const points = ref<CaptchaPoint[]>([]);

function choose(point: { x: number; y: number }) {
  if (
    props.busy ||
    props.challenge.provider !== 'click_word' ||
    points.value.length >= props.challenge.data.words.length
  )
    return;
  points.value.push(
    toOriginalPoint(point.x, point.y, width.value, width.value / 2),
  );
  if (points.value.length === props.challenge.data.words.length)
    emit('answer', { points: [...points.value] });
}

function slide(value: number | number[]) {
  if (!props.busy) emit('answer', { points: [{ x: value as number, y: 0 }] });
}
</script>

<template>
  <div
    :style="{ width: `${width}px` }"
    :class="{ 'pointer-events-none': busy }"
  >
    <template v-if="challenge.provider === 'block_puzzle'">
      <div class="relative overflow-hidden">
        <img
          :src="`data:image/jpeg;base64,${challenge.data.image}`"
          :alt="$t('utils.captcha.image')"
          class="block w-full"
        />
        <img
          :src="`data:image/png;base64,${challenge.data.piece}`"
          alt=""
          class="pointer-events-none absolute top-0 h-full"
          :style="{
            left: `${(x / 320) * 100}%`,
            width: `${(challenge.data.piece_width / 320) * 100}%`,
          }"
        />
      </div>
      <ElSlider
        v-model="x"
        :max="320 - challenge.data.piece_width"
        :disabled="busy"
        :show-tooltip="false"
        :aria-label="$t('utils.captcha.slide')"
        @change="slide"
      />
      <p>{{ $t('utils.captcha.slide') }}</p>
    </template>
    <PointSelectionCaptcha
      v-else
      :captcha-image="`data:image/jpeg;base64,${challenge.data.image}`"
      :hint-text="challenge.data.words.join(' → ')"
      :width="width"
      :height="width / 2"
      :padding-x="0"
      :padding-y="0"
      @click="choose"
      @refresh="emit('refresh')"
    />
  </div>
</template>
