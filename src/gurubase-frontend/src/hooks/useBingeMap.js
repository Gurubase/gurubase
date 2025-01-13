import { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import { getBingeData } from "@/app/actions";
import { setBingeInfo } from "@/redux/slices/mainFormSlice";

export function useBingeMap(guruType, bingeId) {
  const dispatch = useAppDispatch();
  const streamingStatus = useAppSelector(
    (state) => state.mainForm.streamingStatus
  );
  const refreshTrigger = useAppSelector(
    (state) => state.mainForm.bingeMapRefreshTrigger
  );
  const currentQuestionSlug = useAppSelector(
    (state) => state.mainForm.currentQuestionSlug
  );

  const followUpQuestions = useAppSelector(
    (state) => state.mainForm.followUpQuestions
  );

  const fetchGraphData = async () => {
    if (!bingeId || !guruType) {
      dispatch(setBingeInfo({ treeData: null, bingeOutdated: false }));
    }

    try {
      const data = await getBingeData(guruType, bingeId);

      const bingeOutdated = data.binge_outdated;
      if (!data.graph_data) {
        dispatch(setBingeInfo({ treeData: null, bingeOutdated }));
        return;
      }

      // Transform the flat data into a tree structure
      const transformToTree = (items) => {
        const itemMap = {};
        const root = [];

        items.forEach((item) => {
          itemMap[item.id] = {
            id: item.id,
            text: item.question,
            slug: item.slug,
            parent_slug: null,
            children: []
          };
        });

        items.forEach((item) => {
          const node = itemMap[item.id];
          if (item.parent_id === null) {
            root.push(node);
          } else {
            const parent = itemMap[item.parent_id];
            if (parent) {
              parent.children.push(node);
              node.parent_slug = parent.slug;
            }
          }
        });

        return root[0];
      };

      const transformedData = transformToTree(data.graph_data);
      dispatch(setBingeInfo({ treeData: transformedData, bingeOutdated }));
    } catch (error) {
      // console.error("Error fetching graph data:", error);
    }
  };

  useEffect(() => {
    if (streamingStatus) return;
    if (bingeId) {
      fetchGraphData();
    } else {
      dispatch(setBingeInfo({ treeData: null, bingeOutdated: false }));
    }
  }, [
    guruType,
    currentQuestionSlug,
    streamingStatus,
    bingeId,
    refreshTrigger,
    followUpQuestions
  ]);
}
