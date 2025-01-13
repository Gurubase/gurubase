export const getGuruTypeBg = (guruType, allGuruTypes) => {
  const guruTypeObj = allGuruTypes?.find((guru) => guru.slug === guruType);

  if (guruTypeObj) {
    return guruTypeObj.colors[1]; // colors[1] is the light color
  }

  return "#FAFAFA";
};

export const getGuruTypeTextColor = (guruType, allGuruTypes) => {
  const guruTypeObj = allGuruTypes?.find((guru) => guru.slug === guruType);

  if (guruTypeObj) {
    return guruTypeObj.colors[0]; // colors[0] is the base color
  }

  return "#FF0000";
};

export const getGuruTypeComboboxBg = (guruType, allGuruTypes) => {
  const guruTypeObj = allGuruTypes?.find((guru) => guru.slug === guruType);

  if (guruTypeObj) {
    return guruTypeObj.colors[0]; // colors[0] is the base color
  }

  return "#2C7FAF";
};

export const getGuruPromptMap = (guruType, allGuruTypes) => {
  const guruTypeObj = allGuruTypes?.find((guru) => guru.slug === guruType);

  if (guruTypeObj) {
    return guruTypeObj.name || guruType;
  }

  return guruType;
};
