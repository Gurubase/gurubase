import useIsInViewport from "@/utils/hooks/useIsInViewport";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import NotificationHeader from "./NotificationHeader";
import NotificationItem from "./NotificationItem";

const notificationItems = [
  {
    icon: "hugeicons:new-twitter",
    text: "Join X",

    link: "https://x.com/gurubaseio"
  },
  {
    icon: "ic:baseline-discord",
    text: "Join Discord Channel",
    link: "https://discord.gg/9CMRSQPqx6"
  }
];

function NotificationCard() {
  const [isVisible, setIsVisible] = useState(false);
  // get guruType and slug from the useParams hook
  const { guruType, slug } = useParams();
  const isInViewport = useIsInViewport("similar-questions");

  useEffect(() => {
    const lastShownDate = localStorage.getItem("notificationLastShown"); // get last shown date from local storage
    const today = new Date().toDateString(); // get today's date
    const isDontAskAgainExist =
      localStorage.getItem("notificationDontAskAgain") === "true"; // get notificationDontAskAgain from local storage

    setTimeout(() => {
      const similarQuestions = document.querySelector(".similar-questions"); // for mobile device check if similar-questions exists in the DOM tree
      if (isDontAskAgainExist) return; // if notificationDontAskAgain exists in the local storage return
      // if user is in the main page show after 30 seconds
      if (lastShownDate !== today && !similarQuestions) {
        // if last shown date is not today
        const timer = setTimeout(() => {
          setIsVisible(true);
          localStorage.setItem("notificationLastShown", today);
        }, 25000);

        return () => clearTimeout(timer);
      }
    }, 5000);
  }, [guruType, slug]);

  // Check only in mobile device when users reach the similar questions section
  useEffect(() => {
    const lastShownDate = localStorage.getItem("notificationLastShown"); // get last shown date from local storage
    const isDontAskAgainExist =
      localStorage.getItem("notificationDontAskAgain") === "true"; // get notificationDontAskAgain from local storage
    const today = new Date().toDateString(); // get today's date
    // if  slug and guruType exist catch similar-questions className in the bottom of the page when similar-questions appears on the page  if it appears in the DOM tree and set isVisble to true
    if (isDontAskAgainExist) return;

    if (
      isInViewport &&
      lastShownDate !== today &&
      guruType &&
      slug &&
      !isDontAskAgainExist
    ) {
      setIsVisible(true);
      localStorage.setItem("notificationLastShown", today);
    }
  }, [guruType, slug, isInViewport]);

  const dontAskAgain = () => {
    // set last shown date to today and hide notification
    localStorage.setItem("notificationLastShown", new Date().toDateString());
    // also add notificationDontAskAgain to local storage
    localStorage.setItem("notificationDontAskAgain", "true");
    setIsVisible(false);
  };

  if (!isVisible) return null; // if notification is not visible, return null

  return (
    <>
      <div className="xs:fixed xs:top-0 xs:left-0 xs:right-0 xs:bottom-0 xs:bg-black-base xs:opacity-50 xs:z-40"></div>
      <article className="fixed xs:inset-0 flex xs:items-center xs:justify-center guru-md:justify-end guru-lg:justify-end guru-md:items-end guru-lg:items-end xs:right-0 guru-md:right-7 guru-md:bottom-7 guru-lg:right-7 guru-lg:bottom-7 z-50">
        <div className="xs:mx-3  h-fit z-50 bottom-20  flex overflow-hidden flex-col text-base font-medium rounded-xl border xs:border-none border-solid border-neutral-200 max-w-[434px] text-zinc-900">
          <NotificationHeader onClose={() => setIsVisible(false)} />
          {notificationItems.map((item, index) => (
            <NotificationItem
              key={index}
              icon={item.icon}
              text={item.text}
              index={index}
              link={item.link}
            />
          ))}
          <footer
            className=" xs:flex-grow-0  flex-1 shrink gap-2 self-stretch px-4 py-3 w-full text-sm text-center bg-white text-gray-400 cursor-pointer"
            onClick={dontAskAgain}>
            Don&apos;t ask again
          </footer>
        </div>
      </article>
    </>
  );
}

export default NotificationCard;
