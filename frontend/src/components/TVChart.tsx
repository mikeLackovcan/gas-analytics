"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  LineSeries,
  AreaSeries,
  HistogramSeries,
  ColorType,
  Time,
  LineStyle,
  AutoscaleInfo,
} from "lightweight-charts";

export type TVPoint = { time: string; value: number };

export type TVSeries = {
  id: string;
  type: "line" | "area" | "histogram";
  data: TVPoint[];
  color?: string;
  lineWidth?: 1 | 2 | 3 | 4;
  lineStyle?: "solid" | "dashed" | "dotted";
  topColor?: string;        // area fill top
  bottomColor?: string;     // area fill bottom
  base?: number;            // histogram base (default 0)
  priceFormat?: { type: "price" | "volume"; precision?: number; minMove?: number };
  visible?: boolean;
};

export type TVMarker = { time: string; price: number; color?: string; label?: string };

const LINE_STYLE = {
  solid:  LineStyle.Solid,
  dashed: LineStyle.Dashed,
  dotted: LineStyle.Dotted,
} as const;

type Props = {
  height?: number;
  series: TVSeries[];
  priceLines?: { price: number; color?: string; label?: string; lineStyle?: "solid" | "dashed" | "dotted" }[];
  yUnit?: string;          // suffix shown on price scale ("%" / "GWh" / "€/MWh")
  fitContent?: boolean;
};

export default function TVChart({ height = 320, series, priceLines, yUnit = "", fitContent = true }: Props) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<Record<string, ISeriesApi<"Line" | "Area" | "Histogram">>>({});

  useEffect(() => {
    if (!wrapRef.current) return;
    const chart = createChart(wrapRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0a0e15" },
        textColor: "#a8b3bf",
        fontSize: 11,
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        attributionLogo: false,
      },
      rightPriceScale: {
        borderColor: "#1f2933",
      },
      timeScale: {
        borderColor: "#1f2933",
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
        rightOffset: 4,
      },
      grid: {
        vertLines: { color: "#11161f" },
        horzLines: { color: "#11161f" },
      },
      crosshair: {
        mode: 1, // magnet
        vertLine: { color: "#ff9900", width: 1, style: LineStyle.Solid },
        horzLine: { color: "#ff9900", width: 1, style: LineStyle.Solid },
      },
      handleScroll: true,
      handleScale: true,
      width: wrapRef.current.clientWidth,
      height,
    });
    chartRef.current = chart;
    const ro = new ResizeObserver(() => {
      if (wrapRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: wrapRef.current.clientWidth });
      }
    });
    ro.observe(wrapRef.current);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = {};
    };
  }, [height]);

  // Apply series whenever inputs change.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    // Remove series no longer in the prop set
    const presentIds = new Set(series.map((s) => s.id));
    for (const id of Object.keys(seriesRef.current)) {
      if (!presentIds.has(id)) {
        chart.removeSeries(seriesRef.current[id]);
        delete seriesRef.current[id];
      }
    }

    for (const s of series) {
      let api = seriesRef.current[s.id];
      if (!api) {
        if (s.type === "line") {
          api = chart.addSeries(LineSeries, {
            color: s.color ?? "#41b6e6",
            lineWidth: s.lineWidth ?? 2,
            lineStyle: LINE_STYLE[s.lineStyle ?? "solid"],
            priceLineVisible: false,
            lastValueVisible: true,
            priceFormat: s.priceFormat ?? { type: "price", precision: 1, minMove: 0.1 },
          });
        } else if (s.type === "area") {
          api = chart.addSeries(AreaSeries, {
            lineColor: s.color ?? "rgba(65,182,230,0)",
            topColor: s.topColor ?? "rgba(65,182,230,0.25)",
            bottomColor: s.bottomColor ?? "rgba(65,182,230,0.02)",
            lineWidth: s.lineWidth ?? 1,
            priceLineVisible: false,
            lastValueVisible: false,
            priceFormat: s.priceFormat ?? { type: "price", precision: 1, minMove: 0.1 },
          });
        } else {
          api = chart.addSeries(HistogramSeries, {
            color: s.color ?? "#41b6e6",
            base: s.base ?? 0,
            priceFormat: s.priceFormat ?? { type: "volume" },
          });
        }
        seriesRef.current[s.id] = api;
      }
      // Lightweight-charts requires ascending unique time. Coerce strings to its Time type.
      const data = s.data.map((p) => ({ time: p.time as unknown as Time, value: p.value }));
      api.setData(data);
      if (typeof s.visible === "boolean") {
        api.applyOptions({ visible: s.visible });
      }
    }

    // Price lines (e.g., 90% storage target)
    if (priceLines && priceLines.length > 0) {
      const anchor = Object.values(seriesRef.current)[0];
      if (anchor) {
        // Clear and re-create. (createPriceLine returns a handle but we keep it simple.)
        for (const pl of priceLines) {
          anchor.createPriceLine({
            price: pl.price,
            color: pl.color ?? "#ff5f5f",
            lineStyle: LINE_STYLE[pl.lineStyle ?? "dashed"],
            lineWidth: 1,
            axisLabelVisible: true,
            title: pl.label ?? "",
          });
        }
      }
    }

    // Y-axis suffix via price-format override on each series
    if (yUnit) {
      for (const api of Object.values(seriesRef.current)) {
        api.applyOptions({
          priceFormat: {
            type: "custom",
            formatter: (p: number) => `${p.toFixed(1)} ${yUnit}`,
            minMove: 0.1,
          },
        });
      }
    }

    if (fitContent) chart.timeScale().fitContent();
  }, [series, priceLines, yUnit, fitContent]);

  return <div ref={wrapRef} style={{ width: "100%", height }} />;
}
