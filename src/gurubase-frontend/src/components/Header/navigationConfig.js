export const navigationItems = [
  {
    id: "my-gurus",
    label: "My Gurus",
    href: "/my-gurus",
    icon: "solar:notes-linear",
    textColor: "#6D6D6D",
    iconColor: "#6D6D6D"
  },
  {
    id: "binge-history",
    label: "Binge History",
    href: "/binge-history",
    icon: "solar:history-linear",
    textColor: "#6D6D6D",
    iconColor: "#6D6D6D"
  },
  {
    id: "api-keys",
    label: "API Keys",
    href: "/api-keys",
    icon: "solar:key-linear",
    textColor: "#6D6D6D",
    iconColor: "#6D6D6D"
  }
];

export const logoutItem = {
  id: "logout",
  label: "Log out",
  href: "/api/auth/logout",
  icon: "solar:logout-outline",
  textColor: "#DC2626",
  iconColor: "#DC2626"
};

export const settingsItem = {
  id: "settings",
  label: "Settings",
  href: "/settings",
  icon: "solar:settings-linear",
  textColor: "#6D6D6D",
  iconColor: "#6D6D6D"
};

export const getNavigationItems = (isSelfHosted) => {
  const items = [...navigationItems];

  if (isSelfHosted) {
    items.push(settingsItem);
  } else {
    items.push(logoutItem);
  }

  return items;
};
