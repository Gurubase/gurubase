export const getAncestorQuestions = (node, targetSlug) => {
  if (!node) return [];

  const findPath = (current, target, path = []) => {
    if (!current) return null;

    path.push(current.text);

    if (current.slug === target) {
      return path;
    }

    if (current.children) {
      for (const child of current.children) {
        const result = findPath(child, target, [...path]);
        if (result) return result;
      }
    }

    return null;
  };

  return findPath(node, targetSlug) || [];
};
