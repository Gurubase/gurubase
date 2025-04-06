import useIsInViewport from "@/utils/hooks/useIsInViewport";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import NotificationHeader from "./NotificationHeader";
import NotificationItem from "./NotificationItem";

const notificationItems = [
  {
    icon: (
      <svg
        className="w-5 h-5"
        fill="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
      </svg>
    ),
    text: "Star us on GitHub",
    link: "https://github.com/Gurubase/gurubase"
  },
  {
    icon: "ic:baseline-discord",
    text: "Join our Discord",
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
