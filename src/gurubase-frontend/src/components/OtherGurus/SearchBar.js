import React from "react";
import { SolarMagniferOutline } from "@/components/Icons";

const SearchBar = ({
  setFilter,
  filter,
  label = "Search",
  placeholder = "Search",
  loading = false
}) => {
  const handleSubmit = (e) => {
    e.preventDefault();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex gap-2 items-center px-3 py-2.5 w-full bg-white rounded-lg border border-solid border-neutral-200 text-xs">
      <label htmlFor="searchInput" className="sr-only">
        {label}
      </label>

      <SolarMagniferOutline
        className="text-anteon-orange"
        width={14}
        height={14}
      />
      <input
        type="search"
        id="searchInput"
        placeholder={placeholder}
        value={filter}
        disabled={loading}
        onChange={(e) => {
          if (loading) return;
          setFilter(e.target.value);
        }}
        className="flex-1 shrink self-stretch w-full my-auto basis-0 text-ellipsis bg-transparent border-none outline-none text-xs"
      />
    </form>
  );
};

export default SearchBar;
