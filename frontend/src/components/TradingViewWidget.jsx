import React, { useEffect, useRef, memo } from 'react';

function TradingViewWidget({ symbol = 'ETH/USDT', theme = 'dark' }) {
  const container = useRef();
  
  // Format standard pairs into TradingView symbol (e.g., ETH/USDT -> BINANCE:ETHUSDT)
  // Defaulting to Binance Exchange for liquid pairs.
  const formattedSymbol = `BINANCE:${symbol.replace('/', '')}`;

  useEffect(() => {
    // Prevent appending multiple scripts in React strict mode
    if (container.current && !container.current.querySelector('script')) {
      const script = document.createElement("script");
      script.src = "https://s.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
      script.type = "text/javascript";
      script.async = true;
      script.innerHTML = `
        {
          "autosize": true,
          "symbol": "${formattedSymbol}",
          "interval": "D",
          "timezone": "Etc/UTC",
          "theme": "${theme}",
          "style": "1",
          "locale": "en",
          "allow_symbol_change": true,
          "calendar": false,
          "support_host": "https://www.tradingview.com",
          "backgroundColor": "rgba(0, 0, 0, 0)",
          "gridColor": "rgba(255, 255, 255, 0.05)",
          "hide_top_toolbar": false,
          "hide_legend": false,
          "save_image": false
        }`;
      container.current.appendChild(script);
    }
  }, [formattedSymbol, theme]);

  return (
    <div className="tradingview-widget-container" ref={container} style={{ height: "100%", width: "100%", minHeight: "450px" }}>
      <div className="tradingview-widget-container__widget" style={{ height: "calc(100% - 32px)", width: "100%" }}></div>
    </div>
  );
}

export default memo(TradingViewWidget);
