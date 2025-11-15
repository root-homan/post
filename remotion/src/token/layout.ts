export const CARD_BASE_WIDTH = 1096;
export const CARD_EXPANDED_SCALE = 1.25;
export const CARD_VISUAL_HEIGHT = 1860;
export const CARD_HORIZONTAL_INSET_RATIO =
  96 / (CARD_BASE_WIDTH * CARD_EXPANDED_SCALE);

export interface CardBounds {
  width: number;
  height: number;
  left: number;
  top: number;
}

export const calculateCardBounds = (
  videoWidth: number,
  videoHeight: number
): CardBounds => {
  const width = CARD_BASE_WIDTH * CARD_EXPANDED_SCALE;
  const height = CARD_VISUAL_HEIGHT;
  const left = (videoWidth - width) / 2;
  const top = (videoHeight - height) / 2;

  return {
    width,
    height,
    left,
    top,
  };
};

