import clsx from "clsx";
import Image from "next/image";
import Link from "next/link";

const LinkCard = ({ link, children }) => {
  if (!link) return children;

  return (
    <Link
      passHref
      className="cursor-pointer guru-md:self-stretch guru-lg:self-stretch"
      href={link}
      prefetch={false}
      target="_blank">
      {children}
    </Link>
  );
};

function SourceCard({ icon, title, description, link }) {
  return (
    <LinkCard link={link}>
      <article className={clsx("flex flex-row gap-4 pb-2")}>
        <Image
          alt=""
          className="object-contain w-10 aspect-square fill-neutral-50"
          height={40}
          src={icon}
          width={40}
        />
        <div className="flex flex-col w-full">
          <p className="text-body font-medium text-gray-800 guru-sm:text-body2">
            {title}
          </p>
          <p className="mt-1 text-body2 font-normal text-gray-400 guru-sm:text-body3">
            {description}
          </p>
        </div>
      </article>
    </LinkCard>
  );
}

export default SourceCard;
