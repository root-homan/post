import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { useSyncExternalStore } from "react";

/**
 * Focus System
 * ------------
 *
 * This module centralizes everything related to spotlighting portions of the token card.
 * It exposes:
 *
 * - `useFocusArea` for components to tag their DOM nodes with semantic metadata.
 * - `FocusSystemRoot` which wraps the card, maintains measurements, renders the
 *   dimming layer, and feeds the camera rig with snapshots.
 * - `FocusCameraRig` that recenters/zooms based on a single focused region.
 * - Selector helpers (`FocusSelectors`) so timeline authors can request specific
 *   areas without knowing implementation details.
 *
 * The new architecture avoids registering/unregistering areas through React
 * state. Instead, it keeps a tiny external store with a stable version number
 * that components read via `useSyncExternalStore`, preventing nested updates.
 */

export const FocusDomain = {
  Card: "card",
  Header: "header",
  Bio: "bio",
  Hero: "hero",
  Valuation: "valuation",
  HoldersPane: "holders-pane",
  HolderRow: "holder-row",
  HolderMetric: "holder-metric",
  Drawer: "drawer",
} as const;

export type FocusDomain = (typeof FocusDomain)[keyof typeof FocusDomain];
export type FocusTag = string;
export type FocusSelectorMode = "spot" | "group";

export interface FocusSelector {
  domain?: FocusDomain;
  areaId?: string;
  parentId?: string;
  tags?: FocusTag[];
  mode?: FocusSelectorMode;
}

export interface FocusAreaDescriptor {
  domain: FocusDomain;
  areaId?: string;
  parentId?: string;
  tags?: FocusTag[];
  priority?: number;
}

export interface FocusRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface FocusResolvedRegion {
  key: string;
  bounds: FocusRect;
  selector: FocusSelector;
}

export interface FocusSnapshot {
  cardBounds: FocusRect | null;
  regions: FocusResolvedRegion[];
  aggregateBounds: FocusRect | null;
}

const DEFAULT_SELECTOR_MODE: FocusSelectorMode = "spot";
const DIM_OPACITY = 0.65;
const HIGHLIGHT_EDGE_SOFTNESS = 28;
const CAMERA_SCALE_DELTA = 0.08;

const createResizeObserver = (callback: ResizeObserverCallback) => {
  if (typeof ResizeObserver === "undefined") {
    return null;
  }
  return new ResizeObserver(callback);
};

const mergeRects = (rects: FocusRect[]): FocusRect => {
  const xs = rects.map((rect) => rect.x);
  const ys = rects.map((rect) => rect.y);
  const rights = rects.map((rect) => rect.x + rect.width);
  const bottoms = rects.map((rect) => rect.y + rect.height);

  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...rights);
  const maxY = Math.max(...bottoms);

  return {
    x: minX,
    y: minY,
    width: Math.max(0, maxX - minX),
    height: Math.max(0, maxY - minY),
  };
};

const matchesSelector = (area: FocusAreaDescriptor, selector: FocusSelector) => {
  if (selector.domain && selector.domain !== area.domain) {
    return false;
  }
  if (selector.areaId && selector.areaId !== area.areaId) {
    return false;
  }
  if (selector.parentId && selector.parentId !== area.parentId) {
    return false;
  }
  if (selector.tags && selector.tags.length > 0) {
    if (!area.tags || selector.tags.some((tag) => !area.tags?.includes(tag))) {
      return false;
    }
  }
  return true;
};

const resolveRegions = (
  selectors: FocusSelector[],
  areas: FocusAreaSnapshot[]
): FocusResolvedRegion[] => {
  if (selectors.length === 0) {
    return [];
  }

  const regions: FocusResolvedRegion[] = [];

  selectors.forEach((selector, selectorIndex) => {
    const matchedAreas = areas.filter(
      (area) => area.bounds && matchesSelector(area.descriptor, selector)
    );

    if (matchedAreas.length === 0) {
      return;
    }

    const mode = selector.mode ?? DEFAULT_SELECTOR_MODE;

    if (mode === "group") {
      const bounds = mergeRects(matchedAreas.map((area) => area.bounds!) as FocusRect[]);
      regions.push({
        key: `selector-${selectorIndex}-group`,
        bounds,
        selector,
      });
      return;
    }

    matchedAreas.forEach((area) => {
      regions.push({
        key: `selector-${selectorIndex}-${area.id}`,
        bounds: area.bounds as FocusRect,
        selector,
      });
    });
  });

  return regions;
};

interface FocusAreaSnapshot {
  id: string;
  descriptor: FocusAreaDescriptor;
  bounds: FocusRect | null;
}

interface FocusStore {
  subscribe: (listener: () => void) => () => void;
  getVersionSnapshot: () => number;
  setRootElement: (node: HTMLDivElement | null) => void;
  upsertDescriptor: (key: string, descriptor: FocusAreaDescriptor) => void;
  updateDescriptor: (key: string, descriptor: FocusAreaDescriptor) => void;
  removeArea: (key: string) => void;
  setNode: (key: string, node: HTMLElement | null) => void;
  getAreaSnapshots: () => FocusAreaSnapshot[];
  getCardBounds: () => FocusRect | null;
}

const FocusStoreContext = createContext<FocusStore | null>(null);

const createFocusStore = (): FocusStore => {
  let version = 0;
  let rootElement: HTMLDivElement | null = null;
  let rootBounds: FocusRect | null = null;
  let rootObserver: ResizeObserver | null = null;
  const listeners = new Set<() => void>();
  const areas = new Map<
    string,
    {
      descriptor: FocusAreaDescriptor;
      node: HTMLElement | null;
      observer: ResizeObserver | null;
      bounds: FocusRect | null;
    }
  >();

  const notify = () => {
    version += 1;
    listeners.forEach((listener) => listener());
  };

  const measureRootBounds = () => {
    if (!rootElement) {
      if (rootBounds) {
        rootBounds = null;
        notify();
      }
      return;
    }

    const nextBounds: FocusRect = {
      x: 0,
      y: 0,
      width: rootElement.clientWidth,
      height: rootElement.clientHeight,
    };

    if (!areRectsEqual(rootBounds, nextBounds)) {
      rootBounds = nextBounds;
      notify();
    }
  };

  const setRootElement = (node: HTMLDivElement | null) => {
    if (rootObserver) {
      rootObserver.disconnect();
      rootObserver = null;
    }

    rootElement = node;

    if (!node) {
      measureRootBounds();
      return;
    }

    measureRootBounds();
    rootObserver = createResizeObserver(() => measureRootBounds());
    rootObserver?.observe(node);
  };

  const ensureArea = (key: string, descriptor: FocusAreaDescriptor) => {
    const existing = areas.get(key);
    if (existing) {
      existing.descriptor = descriptor;
      return existing;
    }

    const area = {
      descriptor,
      node: null,
      observer: null,
      bounds: null,
    };
    areas.set(key, area);
    return area;
  };

  const updateBounds = (key: string) => {
    const area = areas.get(key);
    if (!area) {
      return;
    }

    if (!area.node || !rootElement) {
      if (area.bounds) {
        area.bounds = null;
        notify();
      }
      return;
    }

    const nodeRect = area.node.getBoundingClientRect();
    const rootRect = rootElement.getBoundingClientRect();

    // Use scrollWidth/scrollHeight to get actual content dimensions even when clipped
    const width = Math.max(nodeRect.width, area.node.scrollWidth);
    const height = Math.max(nodeRect.height, area.node.scrollHeight);

    const next: FocusRect = {
      x: nodeRect.left - rootRect.left,
      y: nodeRect.top - rootRect.top,
      width,
      height,
    };

    if (!areRectsEqual(area.bounds, next)) {
      area.bounds = next;
      notify();
    }
  };

  const setNode = (key: string, node: HTMLElement | null) => {
    const area = areas.get(key);
    if (!area) {
      return;
    }

    if (area.node === node && node !== null) {
      return;
    }

    if (area.observer) {
      area.observer.disconnect();
      area.observer = null;
    }

    area.node = node;

    if (!node) {
      if (area.bounds) {
        area.bounds = null;
        notify();
      }
      return;
    }

    const observer = createResizeObserver(() => updateBounds(key));
    if (observer) {
      area.observer = observer;
      observer.observe(node);
    }
    updateBounds(key);
  };

  const removeArea = (key: string) => {
    const area = areas.get(key);
    if (!area) {
      return;
    }
    area.observer?.disconnect();
    areas.delete(key);
    notify();
  };

  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  return {
    subscribe,
    getVersionSnapshot: () => version,
    setRootElement,
    upsertDescriptor: (key, descriptor) => {
      ensureArea(key, descriptor);
      notify();
    },
    updateDescriptor: (key, descriptor) => {
      ensureArea(key, descriptor);
      notify();
    },
    removeArea,
    setNode,
    getAreaSnapshots: () =>
      Array.from(areas.entries()).map(([id, area]) => ({
        id,
        descriptor: area.descriptor,
        bounds: area.bounds,
      })),
    getCardBounds: () => rootBounds,
  };
};

export const createFocusId = (
  namespace: string,
  label: string,
  fallbackIndex?: number
) => {
  const slug =
    label
      ?.toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || (fallbackIndex !== undefined ? String(fallbackIndex) : "focus");

  return `${namespace}-${slug}${fallbackIndex !== undefined ? `-${fallbackIndex}` : ""}`;
};

export const FocusSelectors = {
  header: (): FocusSelector[] => [{ domain: FocusDomain.Header }],
  bio: (): FocusSelector[] => [{ domain: FocusDomain.Bio }],
  holdersPane: (): FocusSelector[] => [
    { domain: FocusDomain.HoldersPane, mode: "group" },
  ],
  valuations: (): FocusSelector[] => [{ domain: FocusDomain.Valuation }],
  holderRow: (label: string, index?: number): FocusSelector[] => [
    {
      domain: FocusDomain.HolderRow,
      areaId: createFocusId("holder-row", label, index),
    },
  ],
  holderValuation: (label: string, index?: number): FocusSelector[] => [
    {
      domain: FocusDomain.Valuation,
      parentId: createFocusId("holder-row", label, index),
      tags: ["valuation", "holder"],
    },
  ],
};

const areRectsEqual = (a: FocusRect | null, b: FocusRect | null) => {
  if (!a && !b) {
    return true;
  }
  if (!a || !b) {
    return false;
  }
  return (
    a.x === b.x &&
    a.y === b.y &&
    a.width === b.width &&
    a.height === b.height
  );
};

const areSnapshotsEqual = (
  a: FocusSnapshot | null,
  b: FocusSnapshot | null
) => {
  if (!a && !b) {
    return true;
  }
  if (!a || !b) {
    return false;
  }

  if (!areRectsEqual(a.cardBounds, b.cardBounds)) {
    return false;
  }

  if (!areRectsEqual(a.aggregateBounds, b.aggregateBounds)) {
    return false;
  }

  if (a.regions.length !== b.regions.length) {
    return false;
  }

  for (let index = 0; index < a.regions.length; index += 1) {
    const prevRegion = a.regions[index];
    const nextRegion = b.regions[index];

    if (prevRegion.key !== nextRegion.key) {
      return false;
    }

    if (!areRectsEqual(prevRegion.bounds, nextRegion.bounds)) {
      return false;
    }
  }

  return true;
};

const buildSnapshot = (
  store: FocusStore,
  selectors: FocusSelector[]
): FocusSnapshot | null => {
  const areas = store.getAreaSnapshots();
  console.log('[buildSnapshot] Areas registered:', areas.map(a => ({ id: a.id, domain: a.descriptor.domain, hasBounds: !!a.bounds })));
  console.log('[buildSnapshot] Selectors:', selectors);
  const regions = resolveRegions(selectors, areas);
  console.log('[buildSnapshot] Resolved regions:', regions.length);
  if (regions.length === 0) {
    return null;
  }

  const aggregateBounds = mergeRects(regions.map((region) => region.bounds));

  return {
    cardBounds: store.getCardBounds(),
    regions,
    aggregateBounds,
  };
};

export interface FocusSystemRootProps {
  className?: string;
  style?: React.CSSProperties;
  selectors?: FocusSelector[];
  focusProgress?: number;
  onSnapshotChange?: (snapshot: FocusSnapshot | null) => void;
  children: React.ReactNode;
}

export const FocusSystemRoot: React.FC<FocusSystemRootProps> = ({
  className,
  style,
  selectors = [],
  focusProgress = 0,
  onSnapshotChange,
  children,
}) => {
  const storeRef = useRef<FocusStore>();
  if (!storeRef.current) {
    storeRef.current = createFocusStore();
  }
  const store = storeRef.current;

  const version = useSyncExternalStore(
    store.subscribe,
    store.getVersionSnapshot,
    store.getVersionSnapshot
  );

  const snapshot = useMemo(
    () => buildSnapshot(store, selectors),
    [store, selectors, version]
  );

  const lastSnapshotRef = useRef<FocusSnapshot | null>(null);

  useEffect(() => {
    if (!onSnapshotChange) {
      lastSnapshotRef.current = snapshot;
      return;
    }

    const previous = lastSnapshotRef.current;
    if (areSnapshotsEqual(previous, snapshot)) {
      return;
    }

    lastSnapshotRef.current = snapshot;
    onSnapshotChange(snapshot);
  }, [onSnapshotChange, snapshot]);

  return (
    <FocusStoreContext.Provider value={store}>
      <div className={className} style={style} ref={store.setRootElement}>
        {children}
        <FocusSpotlightLayer snapshot={snapshot} progress={focusProgress} />
      </div>
    </FocusStoreContext.Provider>
  );
};

const FocusSpotlightLayer: React.FC<{
  snapshot: FocusSnapshot | null;
  progress: number;
}> = ({ snapshot, progress }) => {
  if (progress <= 0 || !snapshot || snapshot.regions.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        backgroundColor: `rgba(0, 0, 0, ${(DIM_OPACITY * progress).toFixed(3)})`,
        transition: "background-color 120ms ease",
        zIndex: 6,
        isolation: "isolate",
      }}
    >
      {snapshot.regions.map((region) => (
        <div
          key={region.key}
          style={{
            position: "absolute",
            left: `${region.bounds.x}px`,
            top: `${region.bounds.y}px`,
            width: `${region.bounds.width}px`,
            height: `${region.bounds.height}px`,
            borderRadius: "calc(var(--token-card-border-radius) * 0.75)",
            background: "radial-gradient(circle at 50% 40%, rgba(255,255,255,0.85), rgba(255,255,255,0.15))",
            boxShadow: `0 0 ${HIGHLIGHT_EDGE_SOFTNESS * 2}px rgba(255,255,255,${(0.45 * progress).toFixed(3)})`,
            opacity: progress,
            transform: `scale(${(1 + 0.04 * progress).toFixed(3)})`,
            transition: "opacity 200ms ease, transform 200ms ease, box-shadow 200ms ease",
            mixBlendMode: "screen",
          }}
        />
      ))}
    </div>
  );
};

const createAutoId = (() => {
  let counter = 0;
  return () => {
    counter += 1;
    return `focus-area-${counter}`;
  };
})();

export const useFocusArea = <T extends HTMLElement = HTMLElement>(
  descriptor: FocusAreaDescriptor
) => {
  const store = useContext(FocusStoreContext);
  const descriptorMemo = useMemo(() => {
    const tags = descriptor.tags ? [...descriptor.tags] : undefined;
    return {
      ...descriptor,
      tags,
    };
  }, [
    descriptor.areaId,
    descriptor.domain,
    descriptor.parentId,
    descriptor.priority,
    descriptor.tags?.join("|"),
  ]);
  const areaKeyRef = useRef(descriptor.areaId ?? createAutoId());

  useEffect(() => {
    if (!store) {
      return;
    }
    store.upsertDescriptor(areaKeyRef.current, descriptorMemo);
    return () => store.removeArea(areaKeyRef.current);
  }, [store]);

  useEffect(() => {
    if (!store) {
      return;
    }
    store.updateDescriptor(areaKeyRef.current, descriptorMemo);
  }, [store, descriptorMemo]);

  const setNode = useCallback(
    (node: T | null) => {
      if (!store) {
        return;
      }
      store.setNode(areaKeyRef.current, node as unknown as HTMLElement | null);
    },
    [store]
  );

  return store ? setNode : undefined;
};

export interface FocusCameraRigProps {
  focusSnapshot: FocusSnapshot | null;
  focusProgress: number;
  children: React.ReactNode;
}

export const FocusCameraRig: React.FC<FocusCameraRigProps> = ({
  focusSnapshot,
  focusProgress,
  children,
}) => {
  const singleRegion =
    focusSnapshot && focusSnapshot.regions.length === 1
      ? focusSnapshot.regions[0]
      : null;

  const cardBounds = focusSnapshot?.cardBounds ?? null;

  let translateX = 0;
  let translateY = 0;
  let scale = 1;

  if (singleRegion && cardBounds && focusProgress > 0) {
    const cardCenterX = cardBounds.width / 2;
    const cardCenterY = cardBounds.height / 2;
    const regionCenterX = singleRegion.bounds.x + singleRegion.bounds.width / 2;
    const regionCenterY = singleRegion.bounds.y + singleRegion.bounds.height / 2;

    translateX = (cardCenterX - regionCenterX) * focusProgress;
    translateY = (cardCenterY - regionCenterY) * focusProgress;
    scale = 1 + CAMERA_SCALE_DELTA * focusProgress;
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `translate3d(${translateX.toFixed(3)}px, ${translateY.toFixed(3)}px, 0) scale(${scale.toFixed(3)})`,
        willChange: "transform",
        transition: "transform 520ms cubic-bezier(0.22, 0.61, 0.36, 1)",
      }}
    >
      {children}
    </div>
  );
};
