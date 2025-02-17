"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from "@/components/ui/binge-map-card";
import { useParams } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setParentQuestionSlug,
  setIsBingeMapOpen,
  setInputQuery,
  setBingeOutdated
} from "@/redux/slices/mainFormSlice";
import clsx from "clsx";
import { handleQuestionUpdate } from "@/utils/handleQuestionUpdate";
import BingeMapZoomControls from "./BingeMapZoomControls";
import BingeMapGraph from "./BingeMapGraph";
import BingeMapTooltip from "./BingeMapTooltip";
import BingeMapMobileButton from "./BingeMapMobileButton";

// Constants
const CONTAINER_HEIGHT = 400;
const PADDING = 20;
const DRAG_THRESHOLD = 0.05;
const MIN_SCALE = 0.5;
const MAX_SCALE = 2;

export function BingeMap({
  setContent,
  setQuestion,
  setDescription,
  treeData,
  bingeOutdated
}) {
  // State
  const [activeNode, setActiveNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [containerWidth, setContainerWidth] = useState(280);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dragDistance, setDragDistance] = useState(0);
  const [scale, setScale] = useState(1);
  const [initialPanSet, setInitialPanSet] = useState(false);
  const [recentlyStreamed, setRecentlyStreamed] = useState(false);
  const [previousNodeCount, setPreviousNodeCount] = useState(0);

  // Refs
  const containerRef = useRef(null);

  // Redux
  const dispatch = useAppDispatch();
  const { guruType } = useParams();
  const currentQuestionSlug = useAppSelector(
    (state) => state.mainForm.currentQuestionSlug
  );
  const parentQuestionSlug = useAppSelector(
    (state) => state.mainForm.parentQuestionSlug
  );
  const streamingStatus = useAppSelector(
    (state) => state.mainForm.streamingStatus
  );
  const inputQuery = useAppSelector((state) => state.mainForm.inputQuery);
  const questionText = useAppSelector((state) => state.mainForm.questionText);
  const bingeId = useAppSelector((state) => state.mainForm.bingeId);
  const isLoading = useAppSelector((state) => state.mainForm.isLoading);
  const isBingeMapOpen = useAppSelector(
    (state) => state.mainForm.isBingeMapOpen
  );
  const isAnswerValid = useAppSelector((state) => state.mainForm.isAnswerValid);
  const contextError = useAppSelector((state) => state.mainForm.contextError);
  const streamError = useAppSelector((state) => state.mainForm.streamError);

  // Helper functions
  const areNodesDisabled = () => {
    return (
      !isAnswerValid ||
      contextError ||
      streamError ||
      isLoading ||
      streamingStatus
    );
  };

  const getNodeColor = (node) => {
    if (streamingStatus) {
      return node.isStreaming ? "#44E531" : "#BABFC8";
    }
    if (node.id === activeNode || node.id === hoveredNode) {
      return "#44E531";
    } else if (node.slug === currentQuestionSlug) {
      return "#44E531";
    } else {
      return "#BABFC8";
    }
  };

  // Include all the calculation functions (calculateNodePositions, getScaledPositions, etc.)
  // ... (copy the existing calculation functions here)

  // Add this helper function to calculate total descendants
  const countDescendants = (node) => {
    if (!node.children || node.children.length === 0) return 0;
    return node.children.reduce(
      (sum, child) => sum + 1 + countDescendants(child),
      0
    );
  };

  // Calculate coordinates for each node
  const calculateNodePositions = (
    node,
    x,
    y,
    level = 0,
    nodes = [],
    links = [],
    levelHeights = {}
  ) => {
    if (!node)
      return { nodes, links, bounds: { minX: 0, maxX: 0, minY: 0, maxY: 0 } };

    const isRoot = nodes.length === 0;
    const nodeX = isRoot ? containerWidth / 2 : x;

    // Calculate vertical spacing based on level
    const verticalSpacing = Math.max(
      150, // minimum spacing
      200 - level * 20 // decrease spacing as we go deeper
    );

    // Store or use the level height
    if (levelHeights[level] === undefined) {
      levelHeights[level] = y;
    }
    const nodeY = levelHeights[level];

    // Calculate required width for this subtree
    const calculateSubtreeWidth = (node, level) => {
      if (!node.children || node.children.length === 0) {
        return 80; // Minimum width for a leaf node
      }

      const baseSpacing = Math.max(80, 120 - level * 15);
      const subtreeSpacing = 40;

      // Calculate width required for each child's subtree
      const childWidths = node.children.map((child) =>
        calculateSubtreeWidth(child, level + 1)
      );

      // Total width is sum of child widths plus spacing between them
      return Math.max(
        baseSpacing,
        childWidths.reduce((sum, width) => sum + width, 0) +
          (node.children.length - 1) * subtreeSpacing
      );
    };

    const subtreeWidth = calculateSubtreeWidth(node, level);

    nodes.push({ ...node, x: nodeX, y: nodeY });

    let bounds = {
      minX: nodeX - subtreeWidth / 2,
      maxX: nodeX + subtreeWidth / 2,
      minY: nodeY,
      maxY: nodeY
    };

    if (node.children && node.children.length > 0) {
      const subtreeSpacing = 40;

      // Calculate widths for each child's subtree
      const childSubtreeWidths = node.children.map((child) =>
        calculateSubtreeWidth(child, level + 1)
      );

      // Calculate total width
      const totalWidth =
        childSubtreeWidths.reduce((sum, width) => sum + width, 0) +
        (node.children.length - 1) * subtreeSpacing;

      // Start position for first child
      let currentX = nodeX - totalWidth / 2;

      node.children.forEach((child, index) => {
        const childSubtreeWidth = childSubtreeWidths[index];
        const childX = currentX + childSubtreeWidth / 2;
        const childY = nodeY + verticalSpacing;

        links.push({
          id: `${node.id}-${child.id}`,
          x1: nodeX,
          y1: nodeY,
          x2: childX,
          y2: childY
        });

        const childResult = calculateNodePositions(
          child,
          childX,
          childY,
          level + 1,
          nodes,
          links,
          levelHeights
        );

        bounds = {
          minX: Math.min(bounds.minX, childResult.bounds.minX),
          maxX: Math.max(bounds.maxX, childResult.bounds.maxX),
          minY: Math.min(bounds.minY, childResult.bounds.minY),
          maxY: Math.max(bounds.maxY, childResult.bounds.maxY)
        };

        currentX += childSubtreeWidth + subtreeSpacing;
      });
    }

    return { nodes, links, bounds };
  };

  // Add this helper function to calculate node size
  const calculateNodeSize = (totalNodes) => {
    // Base size for small trees
    const baseSize = 12;
    // Minimum size for very large trees
    const minSize = 8;
    // Scale factor
    const scaleFactor = 0.1;

    // Calculate size based on total nodes
    const size = Math.max(minSize, baseSize - totalNodes * scaleFactor);
    return size;
  };

  const getScaledPositions = (modifiedTreeData) => {
    // Use existing calculateNodePositions with modified tree
    const { nodes, links, bounds } = calculateNodePositions(
      modifiedTreeData,
      containerWidth / 2,
      PADDING + 20,
      0,
      [],
      [],
      {}
    );

    if (!nodes.length) return { nodes: [], links: [], nodeSize: 12 };

    const graphWidth = bounds.maxX - bounds.minX;
    const graphHeight = bounds.maxY - bounds.minY;

    // More lenient scaling - allow for scrolling
    const minScale = 0.4; // Minimum scale to ensure nodes aren't too small
    const maxScale = 1.2; // Maximum scale to prevent nodes from being too large

    // Calculate scale with more emphasis on width
    const scaleX = (containerWidth - PADDING * 2) / graphWidth;
    const scaleY = (CONTAINER_HEIGHT - PADDING * 2) / graphHeight;
    const scale = Math.min(
      Math.max(minScale, Math.min(scaleX, scaleY)),
      maxScale
    );

    // Center the graph after scaling
    const scaledWidth = graphWidth * scale;
    const scaledHeight = graphHeight * scale;
    const centerX = (containerWidth - scaledWidth) / 2;
    const centerY =
      PADDING + (CONTAINER_HEIGHT - PADDING * 2 - scaledHeight) / 2;

    const scaledNodes = nodes.map((node) => ({
      ...node,
      x: (node.x - bounds.minX) * scale + centerX,
      y: (node.y - bounds.minY) * scale + centerY
    }));

    const scaledLinks = links.map((link) => ({
      ...link,
      x1: (link.x1 - bounds.minX) * scale + centerX,
      y1: (link.y1 - bounds.minY) * scale + centerY,
      x2: (link.x2 - bounds.minX) * scale + centerX,
      y2: (link.y2 - bounds.minY) * scale + centerY
    }));

    return {
      nodes: scaledNodes,
      links: scaledLinks,
      nodeSize: calculateNodeSize(nodes.length)
    };
  };

  // Yeni helper fonksiyon ekle
  const areAllNodesVisible = (
    nodes,
    containerWidth,
    containerHeight,
    currentPan
  ) => {
    return nodes.every((node) => {
      const nodeX = node.x + currentPan.x;
      const nodeY = node.y + currentPan.y;

      // Node'un görünür alanda olup olmadığını kontrol et
      return (
        nodeX >= 0 &&
        nodeX <= containerWidth &&
        nodeY >= 0 &&
        nodeY <= containerHeight
      );
    });
  };

  // Bağlı node'ları bulan yardımcı fonksiyon
  const findConnectedNodes = (nodeId, allNodes) => {
    if (!nodeId || !allNodes?.length) return [];

    const node = allNodes.find((n) => n.id === nodeId);
    if (!node) return [];

    // Parent node'u bul
    const parent = allNodes.find((n) =>
      n.children?.some((child) => child.id === nodeId)
    );

    // Kardeş node'ları bul
    const siblings = parent
      ? allNodes.filter((n) =>
          parent.children?.some((child) => child.id === n.id)
        )
      : [];

    // Çocuk node'ları bul
    const children = allNodes.filter((n) =>
      node.children?.some((child) => child.id === n.id)
    );

    // Tüm bağlı node'ları unique olarak döndür
    return [
      ...new Set([node, ...siblings, ...children, parent].filter(Boolean))
    ];
  };

  // calculateOptimalPan fonksiyonunu güncelle
  const calculateOptimalPan = (
    selectedNode,
    nodes,
    containerWidth,
    containerHeight,
    currentPan
  ) => {
    if (!selectedNode || !nodes.length) return currentPan;

    // Önce tüm node'ların görünür olup olmadığını kontrol et
    if (
      areAllNodesVisible(nodes, containerWidth, containerHeight, currentPan)
    ) {
      return currentPan; // Eğer hepsi görünürse mevcut pan'i koru
    }

    // Eğer görünmeyen node'lar varsa, seçili node'u ve bağlı node'ları merkeze al
    const connectedNodes = findConnectedNodes(selectedNode.id, nodes);

    const bounds = connectedNodes.reduce(
      (acc, node) => ({
        minX: Math.min(acc.minX, node.x),
        maxX: Math.max(acc.maxX, node.x),
        minY: Math.min(acc.minY, node.y),
        maxY: Math.max(acc.maxY, node.y)
      }),
      {
        minX: Infinity,
        maxX: -Infinity,
        minY: Infinity,
        maxY: -Infinity
      }
    );

    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;

    return {
      x: containerWidth / 2 - centerX,
      y: containerHeight / 2 - centerY
    };
  };

  // Use useMemo to calculate scaled positions
  const { nodes, links, nodeSize } = useMemo(() => {
    if (!treeData || !containerWidth)
      return { nodes: [], links: [], nodeSize: 12 };

    // Create a modified tree data that includes the streaming node
    let modifiedTreeData = treeData;

    // Only add streaming node if we're actively streaming OR
    // we recently streamed but haven't received the new node yet
    if (
      (streamingStatus || recentlyStreamed) &&
      !treeData.slug?.includes(currentQuestionSlug) &&
      currentQuestionSlug &&
      parentQuestionSlug
    ) {
      // Deep clone the tree and add streaming node to correct parent
      const addStreamingNode = (node) => {
        if (node.slug === parentQuestionSlug) {
          return {
            ...node,
            children: [
              ...(node.children || []),
              {
                id: "streaming-temp",
                text: currentQuestionSlug,
                slug: currentQuestionSlug,
                isStreaming: streamingStatus,
                children: []
              }
            ]
          };
        }
        if (node.children) {
          return {
            ...node,
            children: node.children.map(addStreamingNode)
          };
        }
        return node;
      };

      modifiedTreeData = addStreamingNode(treeData);
    }

    return getScaledPositions(modifiedTreeData);
  }, [
    treeData,
    containerWidth,
    streamingStatus,
    recentlyStreamed,
    currentQuestionSlug,
    parentQuestionSlug
  ]);

  const activeNodeData = useMemo(
    () =>
      activeNode && nodes?.length
        ? nodes.find((node) => node.id === activeNode)
        : null,
    [activeNode, nodes]
  );

  // Event handlers
  const handleNodeClick = async (nodeId) => {
    if (streamingStatus || isLoading) return;

    const isDesktop =
      typeof window !== "undefined" &&
      window.matchMedia("(min-width: 768px)").matches;
    const clickedNode = nodes.find((node) => node.id === nodeId);

    if (clickedNode) {
      const optimalPan = calculateOptimalPan(
        clickedNode,
        nodes,
        containerWidth,
        CONTAINER_HEIGHT,
        pan
      );
      setPan(optimalPan);

      if (isDesktop) {
        if (clickedNode.slug) {
          dispatch(setIsBingeMapOpen(false));
          dispatch(setInputQuery(""));

          await handleQuestionUpdate({
            guruType,
            newSlug: clickedNode.slug,
            oldSlug: currentQuestionSlug,
            treeData,
            dispatch,
            setContent,
            setQuestion,
            setDescription,
            bingeId,
            questionText
          });
        }
      } else {
        setActiveNode((prevActiveNode) =>
          prevActiveNode === nodeId ? null : nodeId
        );
      }
    }
  };

  const handleNodeHover = (nodeId) => {
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(min-width: 768px)").matches
    ) {
      setHoveredNode(nodeId);
    }
  };

  const handleNodeSelect = async (selectedNode) => {
    dispatch(setIsBingeMapOpen(false));
    setPan({ x: 0, y: 0 });
    setActiveNode(null);
    setHoveredNode(null);
    dispatch(setInputQuery(""));

    await handleQuestionUpdate({
      guruType,
      newSlug: selectedNode.slug,
      oldSlug: currentQuestionSlug,
      treeData,
      dispatch,
      setContent,
      setQuestion,
      setDescription,
      bingeId,
      questionText
    });
  };

  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 0.2, MAX_SCALE));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 0.2, MIN_SCALE));
  };

  // Pan and drag handlers
  const handleMouseDown = (e) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragDistance(0);
      setDragStart({
        x: e.clientX - pan.x,
        y: e.clientY - pan.y
      });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      const newX = e.clientX - dragStart.x;
      const newY = e.clientY - dragStart.y;
      const dx = newX - pan.x;
      const dy = newY - pan.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      setDragDistance(distance);
      setPan({ x: newX, y: newY });
    }
  };

  const handleMouseUp = (e) => {
    if (isDragging) {
      if (dragDistance < DRAG_THRESHOLD) {
        if (e.target.tagName === "svg" || e.target.tagName === "g") {
          setActiveNode(null);
        }
      }
      setIsDragging(false);
    }
  };

  // Touch handlers
  const handleTouchStart = (e) => {
    const touch = e.touches[0];
    setIsDragging(true);
    setDragDistance(0);
    setDragStart({
      x: touch.clientX - pan.x,
      y: touch.clientY - pan.y
    });
  };

  const handleTouchMove = (e) => {
    if (isDragging && e.touches.length > 0) {
      const touch = e.touches[0];
      const newX = touch.clientX - dragStart.x;
      const newY = touch.clientY - dragStart.y;
      const dx = newX - pan.x;
      const dy = newY - pan.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      setDragDistance(distance);
      setPan({ x: newX, y: newY });
    }
  };

  // Effects
  useEffect(() => {
    if (!streamingStatus && bingeOutdated !== undefined) {
      dispatch(setBingeOutdated(bingeOutdated));
      setRecentlyStreamed(true);
    }
  }, [bingeOutdated, dispatch, streamingStatus]);

  useEffect(() => {
    if (recentlyStreamed && treeData && currentQuestionSlug) {
      // Check if the new node exists in the tree
      const nodeExists = (node) => {
        if (node.slug === currentQuestionSlug) return true;
        if (node.children) {
          return node.children.some(nodeExists);
        }
        return false;
      };

      if (nodeExists(treeData)) {
        setRecentlyStreamed(false);
      }
    }
  }, [treeData, recentlyStreamed, currentQuestionSlug]);

  useEffect(() => {
    if (isLoading || streamingStatus) return;

    if (treeData) {
      const findNodeAndParent = (node, targetSlug, parent = null) => {
        if (node.slug === targetSlug) {
          return { node, parent };
        }
        if (node.children) {
          for (const child of node.children) {
            const found = findNodeAndParent(child, targetSlug, node);
            if (found.node) return found;
          }
        }
        return { node: null, parent: null };
      };

      const { node: currentNode, parent: parentNode } = findNodeAndParent(
        treeData,
        currentQuestionSlug
      );

      if (currentNode) {
        dispatch(setParentQuestionSlug(parentNode?.slug || null));
      }
    }
  }, [treeData, currentQuestionSlug, dispatch, isLoading, streamingStatus]);

  useEffect(() => {
    if (isLoading || streamingStatus) return;
    if (guruType && !currentQuestionSlug) {
      dispatch(setParentQuestionSlug(null));
    }
  }, [guruType, currentQuestionSlug, dispatch, isLoading, streamingStatus]);

  useEffect(() => {
    if (!isBingeMapOpen) {
      setActiveNode(null);
      setHoveredNode(null);
    }
  }, [isBingeMapOpen]);

  useEffect(() => {
    const updateContainerWidth = () => {
      if (containerRef.current) {
        const width = containerRef.current.offsetWidth;
        if (width > 0) {
          setContainerWidth(width);
        }
      }
    };

    // Use ResizeObserver for more reliable width updates
    const resizeObserver = new ResizeObserver(updateContainerWidth);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    // Initial update
    updateContainerWidth();

    return () => {
      if (containerRef.current) {
        resizeObserver.unobserve(containerRef.current);
      }
      resizeObserver.disconnect();
    };
  }, [isBingeMapOpen]);

  useEffect(() => {
    if (isLoading || streamingStatus) return;

    if (nodes?.length && currentQuestionSlug && !initialPanSet) {
      const currentNode = nodes.find(
        (node) => node.slug === currentQuestionSlug
      );
      if (currentNode) {
        const optimalPan = calculateOptimalPan(
          currentNode,
          nodes,
          containerWidth,
          CONTAINER_HEIGHT,
          pan
        );
        setPan(optimalPan);
        setInitialPanSet(true);
      }
    }
  }, [
    nodes,
    currentQuestionSlug,
    containerWidth,
    initialPanSet,
    streamingStatus,
    isLoading,
    pan
  ]);

  useEffect(() => {
    if (!isBingeMapOpen) {
      setInitialPanSet(false);
    }
  }, [isBingeMapOpen]);

  if (!treeData || !nodes?.length) {
    return null;
  }

  // Check if treeData only has one node (no children or empty children array)
  if (nodes.length <= 1) {
    return null;
  }

  return (
    <Card
      className={clsx(
        "w-full h-full",
        "bg-transparent",
        isBingeMapOpen &&
          "md:relative fixed inset-x-0 bottom-0 top-[20px] z-[60]"
      )}
      ref={containerRef}>
      <CardHeader
        className="rounded-xl flex flex-col justify-between pb-0 px-0 bg-white"
        isBingeMapOpen={isBingeMapOpen}>
        {
          <>
            <div className={clsx("pb-2", isBingeMapOpen ? "px-5" : "px-3")}>
              <CardTitle className="text-lg font-medium text-neutral-900 text-base font-medium text-zinc-900">
                Binge Map
              </CardTitle>
            </div>
            <div className="w-full h-[1px] bg-neutral-200" />
          </>
        }
      </CardHeader>
      <CardContent
        className={clsx(
          "relative flex-1 h-full",
          isBingeMapOpen ? "polygon-fill" : "bg-transparent"
        )}>
        <BingeMapZoomControls
          scale={scale}
          handleZoomIn={handleZoomIn}
          handleZoomOut={handleZoomOut}
          MIN_SCALE={MIN_SCALE}
          MAX_SCALE={MAX_SCALE}
        />

        <div
          className="w-full h-full cursor-grab active:cursor-grabbing relative flex flex-col min-h-0"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleMouseUp}>
          <BingeMapGraph
            links={links}
            nodes={nodes}
            nodeSize={nodeSize}
            pan={pan}
            scale={scale}
            isDragging={isDragging}
            getNodeColor={getNodeColor}
            areNodesDisabled={areNodesDisabled}
            handleNodeClick={handleNodeClick}
            handleNodeHover={handleNodeHover}
          />

          {(activeNodeData || hoveredNode) && (
            <BingeMapTooltip
              node={activeNodeData || nodes.find((n) => n.id === hoveredNode)}
              scale={scale}
              pan={pan}
              nodes={nodes}
            />
          )}

          <BingeMapMobileButton
            activeNode={activeNode}
            nodes={nodes}
            streamingStatus={streamingStatus}
            handleNodeSelect={handleNodeSelect}
          />
        </div>
      </CardContent>
    </Card>
  );
}

export default BingeMap;
