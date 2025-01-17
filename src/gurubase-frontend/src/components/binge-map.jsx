"use client";
import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/binge-map-card";
import { Button } from "@/components/ui/button";
import MapArrowUp from "@/assets/images/map-arrow-up.svg";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  setParentQuestionSlug,
  setIsBingeMapOpen,
  setInputQuery,
  setQuestionText,
  setBingeOutdated
} from "@/redux/slices/mainFormSlice";
import clsx from "clsx";
import { useBingeMap } from "@/hooks/useBingeMap";
import { handleQuestionUpdate } from "@/utils/handleQuestionUpdate";

export function BingeMap({
  setContent,
  setQuestion,
  setDescription,
  treeData,
  bingeOutdated,
  ...props
}) {
  const [activeNode, setActiveNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [containerWidth, setContainerWidth] = useState(280);
  const containerRef = useRef(null);
  const { guruType } = useParams();
  const currentQuestionSlug = useAppSelector(
    (state) => state.mainForm.currentQuestionSlug
  );

  const parentQuestionSlug = useAppSelector(
    (state) => state.mainForm.parentQuestionSlug
  );
  const router = useRouter();
  const dispatch = useAppDispatch();
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

  const CONTAINER_HEIGHT = 400;
  const PADDING = 20; // Padding from edges

  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dragDistance, setDragDistance] = useState(0);
  const DRAG_THRESHOLD = 5; // pixels

  // const { treeData, bingeOutdated } = useBingeMap(guruType, bingeId);

  useEffect(() => {
    if (!streamingStatus && bingeOutdated !== undefined) {
      dispatch(setBingeOutdated(bingeOutdated));
    }
  }, [bingeOutdated, dispatch, streamingStatus]);

  useEffect(() => {
    //console.log("Will find node by slug", treeData);
    if (isLoading || streamingStatus) {
      //console.log("is loading or streaming status");
      return;
    }

    if (treeData) {
      // Find the current node and its parent
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
        //console.log("setting parent question slug", parentNode?.slug || null);
        dispatch(setParentQuestionSlug(parentNode?.slug || null));
      }
    }
  }, [treeData, currentQuestionSlug, dispatch]);

  useEffect(() => {
    if (isLoading || streamingStatus) return;

    // Reset parent question when on base guru type page (no slug)
    //console.log(
    // "will reset parent question if guru type and no current question slug"
    // );
    if (guruType && !currentQuestionSlug) {
      //console.log("setting parent question slug to null");
      dispatch(setParentQuestionSlug(null));
    }
  }, [guruType, currentQuestionSlug, dispatch]);

  // Add this effect near the other useEffect hooks
  useEffect(() => {
    // Reset active node when binge map is closed on mobile
    if (!isBingeMapOpen) {
      setActiveNode(null);
      setHoveredNode(null);
    }
  }, [isBingeMapOpen]);

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

  // Add this state near the other state declarations
  const [initialPanSet, setInitialPanSet] = useState(false);

  // Modify getScaledPositions to be more lenient with scaling
  const getScaledPositions = () => {
    // Create a modified tree data that includes the streaming node
    let modifiedTreeData = treeData;

    if (
      streamingStatus &&
      currentQuestionSlug &&
      parentQuestionSlug &&
      treeData
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
                isStreaming: true,
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

  // Destructure nodeSize from getScaledPositions
  const { nodes, links, nodeSize } = getScaledPositions();

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

  // handleNodeClick fonksiyonunu güncelle
  const handleNodeClick = async (nodeId) => {
    if (streamingStatus || isLoading) return;

    const isDesktop =
      typeof window !== "undefined" &&
      window.matchMedia("(min-width: 768px)").matches;

    const clickedNode = nodes.find((node) => node.id === nodeId);

    if (clickedNode) {
      // Optimal pan pozisyonunu hesapla (mevcut pan'i de göz önünde bulundurarak)
      const optimalPan = calculateOptimalPan(
        clickedNode,
        nodes,
        containerWidth,
        CONTAINER_HEIGHT,
        pan // Mevcut pan pozisyonunu geçir
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

  const activeNodeData =
    activeNode && nodes?.length
      ? nodes.find((node) => node.id === activeNode)
      : null;

  // Add these new selectors
  const isAnswerValid = useAppSelector((state) => state.mainForm.isAnswerValid);
  const contextError = useAppSelector((state) => state.mainForm.contextError);
  const streamError = useAppSelector((state) => state.mainForm.streamError);

  // Add a helper function to check if nodes should be disabled
  const areNodesDisabled = () => {
    return !isAnswerValid || contextError || streamError || isLoading || streamingStatus;
  };

  // Update getNodeColor to handle disabled state
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

      // Calculate distance moved
      const dx = newX - pan.x;
      const dy = newY - pan.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      setDragDistance(distance);

      setPan({ x: newX, y: newY });
    }
  };

  const handleMouseUp = (e) => {
    if (isDragging) {
      // If barely moved, treat as a click
      if (dragDistance < DRAG_THRESHOLD) {
        // Only reset if clicking on the background
        if (e.target.tagName === "svg" || e.target.tagName === "g") {
          setActiveNode(null);
        }
      }
      setIsDragging(false);
    }
  };

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

      // Calculate distance moved
      const dx = newX - pan.x;
      const dy = newY - pan.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      setDragDistance(distance);

      setPan({ x: newX, y: newY });
    }
  };

  useEffect(() => {
    const updateContainerWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }
    };

    // Initial update
    updateContainerWidth();

    // Update on window resize
    window.addEventListener("resize", updateContainerWidth);

    // Cleanup
    return () => window.removeEventListener("resize", updateContainerWidth);
  }, [isBingeMapOpen]); // Re-run when binge map opens/closes

  // Modify the useEffect that handles initial pan to use the same logic
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
          pan // Mevcut pan pozisyonunu geçir
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
    streamingStatus
  ]);

  // Reset initialPanSet when the map is closed
  useEffect(() => {
    if (!isBingeMapOpen) {
      setInitialPanSet(false);
    }
  }, [isBingeMapOpen]);

  // State eklemeleri (diğer state'lerin yanına)
  const [scale, setScale] = useState(1);
  const MIN_SCALE = 0.5;
  const MAX_SCALE = 2;

  // Zoom fonksiyonları
  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 0.2, MAX_SCALE));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 0.2, MIN_SCALE));
  };

  if (!treeData || !nodes?.length) {
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
        {/* Zoom butonlarını drag alanının dışına taşı */}
        <div className="absolute top-2 right-3 flex flex-col gap-2 z-[51]">
          <button
            onClick={handleZoomIn}
            className="p-2 bg-white rounded-full shadow-lg hover:bg-gray-50 transition-colors cursor-pointer"
            disabled={scale >= MAX_SCALE}>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="11" y1="8" x2="11" y2="14" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 bg-white rounded-full shadow-lg hover:bg-gray-50 transition-colors cursor-pointer"
            disabled={scale <= MIN_SCALE}>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </button>
        </div>

        {/* Drag alanı */}
        <div
          className="w-full h-full cursor-grab active:cursor-grabbing overflow-hidden"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleMouseUp}>
          <svg
            width="1000"
            height="1000"
            className="w-full h-full overflow-visible bg-transparent"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
              transition: isDragging ? "none" : "transform 0.3s ease-out",
              transformOrigin: "0 0"
            }}>
            <g>
              {/* Draw connection lines */}
              {links.map((link) => (
                <line
                  key={link.id}
                  x1={link.x1}
                  y1={link.y1}
                  x2={link.x2}
                  y2={link.y2}
                  stroke="hsl(var(--muted-foreground))"
                  strokeWidth={Math.max(1, nodeSize / 12)} // Scale line width with node size
                  opacity={link.id.includes("streaming-temp") ? "0.3" : "0.5"}
                  strokeDasharray={
                    link.id.includes("streaming-temp") ? "5,5" : "none"
                  }
                />
              ))}

              {/* Draw nodes */}
              {nodes.map((node) => (
                <g key={node.id}>
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={nodeSize}
                    fill={getNodeColor(node)}
                    className={`transition-colors duration-200 ${
                      areNodesDisabled()
                        ? "cursor-not-allowed"
                        : "cursor-pointer"
                    }`}
                    onClick={() => {
                      if (!areNodesDisabled()) {
                        handleNodeClick(node.id);
                      }
                    }}
                    onMouseEnter={() => {
                      if (!areNodesDisabled()) {
                        handleNodeHover(node.id);
                      }
                    }}
                    onMouseLeave={() => {
                      if (!areNodesDisabled()) {
                        handleNodeHover(null);
                      }
                    }}
                  />
                </g>
              ))}
            </g>
          </svg>

          {/* Tooltip card */}
          {(activeNodeData || hoveredNode) &&
            (() => {
              const node =
                activeNodeData || nodes.find((n) => n.id === hoveredNode);
              const nodeY = node?.y * scale + pan.y;
              const nodeX = node?.x * scale + pan.x;

              const isRootNode = !nodes.some((n) =>
                n.children?.some((child) => child.id === node.id)
              );

              // Root node için false, diğerleri için true
              const tooltipOnBottom = !isRootNode;
              // console.log(tooltipOnBottom);

              return (
                <div
                  className="absolute rounded-lg shadow-lg p-3 border md:bg-[#1B242D] md:text-white bg-background"
                  style={{
                    left: `${nodeX}px`,
                    top: `${nodeY + (tooltipOnBottom ? -24 : 24)}px`,
                    transform: `translate(-50%, ${tooltipOnBottom ? "-100%" : "0"}) scale(${scale})`,
                    maxWidth: "300px",
                    minWidth: "100px",
                    width: "max-content",
                    transformOrigin: tooltipOnBottom
                      ? "bottom center"
                      : "top center",
                    zIndex: 50
                  }}>
                  {/* Triangle pointer */}
                  <div
                    className="absolute w-4 h-4 border-l border-t md:bg-[#1B242D] bg-background"
                    style={{
                      [tooltipOnBottom ? "bottom" : "top"]: "-8px",
                      left: "50%",
                      transform: `translateX(-50%) rotate(${tooltipOnBottom ? "225deg" : "45deg"})`,
                      borderColor: "inherit"
                    }}
                  />
                  <p
                    className="text-center relative font-inter px-2"
                    style={{
                      fontSize: "12px",
                      fontWeight: 500,
                      lineHeight: "normal"
                    }}>
                    {node?.text}
                  </p>
                </div>
              );
            })()}

          {/* Mobile-only Open button - moved inside the binge map container */}
          <div
            className="fixed left-1/2 transform -translate-x-1/2 md:hidden"
            style={{
              bottom: "calc(6vh + 24px)" // viewport yüksekliğinin %15'i + footer yüksekliği
            }}>
            <Button
              className={clsx(
                "w-[90px] rounded-full text-white flex items-center justify-center",
                activeNode
                  ? "bg-zinc-900 hover:bg-zinc-800 cursor-pointer"
                  : "bg-zinc-500 hover:bg-zinc-500 cursor-not-allowed"
              )}
              onClick={async () => {
                if (activeNode) {
                  const selectedNode = nodes.find(
                    (node) => node.id === activeNode
                  );
                  if (selectedNode?.slug) {
                    // Close binge map before navigation
                    dispatch(setIsBingeMapOpen(false));
                    // Reset pan position
                    setPan({ x: 0, y: 0 });
                    // Reset active and hovered nodes
                    setActiveNode(null);
                    setHoveredNode(null);
                    dispatch(setInputQuery(""));

                    // Update content before navigation
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

                    // router.push(`/g/${guruType}/${selectedNode.slug}`);
                  }
                }
              }}
              disabled={!activeNode || streamingStatus}>
              <Image
                src={MapArrowUp}
                alt="Map Arrow Up"
                width={13}
                height={13}
                className="mr-2"
              />
              <span>Open</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default BingeMap;
