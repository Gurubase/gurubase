import Image from "next/image";

const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

export const GuruIconGetter = ({ guru, width, height, iconUrl, guruName }) => {
  return (
    iconUrl &&
    (isSelfHosted ? (
      <Image
        alt={guruName + " guru icon"}
        className="self-center"
        height={height}
        src={iconUrl}
        width={width}
      />
    ) : (
      <img
        alt={guruName + " guru icon"}
        className="self-center"
        height={height}
        loading="lazy"
        src={iconUrl}
        width={width}
      />
    ))
  );
};
