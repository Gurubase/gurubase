import { getIconData, iconToSVG, iconToHTML, replaceIDs } from "@iconify/utils";

export function generateIconSVG(
  iconCollection,
  iconName,
  height = "auto",
  width = "auto"
) {
  // Get content for icon
  const iconData = getIconData(iconCollection, iconName);
  if (!iconData) {
    throw new Error(`Icon "${iconName}" is missing`);
  }

  // Use it to render icon
  const renderData = iconToSVG(iconData, {
    height: height,
    width: width
  });

  // Generate SVG string
  const svg = iconToHTML(replaceIDs(renderData.body), renderData.attributes);

  // Return SVG
  return svg;
}
