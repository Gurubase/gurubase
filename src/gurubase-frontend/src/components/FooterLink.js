import Image from "next/image";

const FooterLink = ({ text, altText, src }) => {
  return (
    <div className="flex gap-2 justify-center px-4 py-2.5 bg-gray-800 rounded-md">
      {src ? (
        <Image
          loading="lazy"
          src={src}
          alt={altText}
          className="shrink-0 self-start w-4 aspect-square"
          width={16}
          height={16}
        />
      ) : null}
      <div>{text}</div>
    </div>
  );
};

export default FooterLink;
