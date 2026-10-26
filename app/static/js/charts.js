/* Gráficos SVG sencillos (barras y líneas), sin librerías.
   Lee los datos de <script type="application/json" id="..."> y los dibuja
   en el elemento que tenga data-grafico="...". */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  function el(nombre, attrs, texto) {
    var e = document.createElementNS(NS, nombre);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  function miles(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, "."); }
  function corto(n) {
    var a = Math.abs(n);
    if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(".", ",") + " M";
    if (a >= 1e3) return Math.round(n / 1e3) + " mil";
    return String(Math.round(n));
  }
  function escalaMax(max) {
    if (max <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(max))), f = max / p;
    var n = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
    return n * p;
  }

  function dibujar(cont, d) {
    cont.textContent = "";
    var W = Math.max(cont.clientWidth, 260), H = W < 480 ? 210 : 250;
    var m = { t: 12, r: 10, b: 28, l: d.dinero ? 50 : 30 };
    var iw = W - m.l - m.r, ih = H - m.t - m.b;
    var todos = [];
    d.series.forEach(function (s) { todos = todos.concat(s.valores); });
    var bruto = Math.max.apply(null, todos.concat([0]));
    // Conteos (clientes): múltiplos de 4 para que las 4 marcas sean enteras
    var max = d.dinero ? escalaMax(bruto) : Math.max(4, Math.ceil(bruto / 4) * 4);
    var fmt = d.dinero ? corto : function (n) { return String(Math.round(n * 100) / 100); };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": d.series.map(function (s) { return s.nombre; }).join(" y ") + " por período" });

    for (var g = 0; g <= 4; g++) {
      var y = m.t + ih - (ih * g) / 4;
      svg.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: y, y2: y, "class": g ? "grid" : "axis" }));
      svg.appendChild(el("text", { x: m.l - 6, y: y + 4, "text-anchor": "end" }, fmt((max * g) / 4)));
    }

    var n = d.etiquetas.length, paso = iw / Math.max(n, 1);
    var cada = Math.ceil(n / Math.max(Math.floor(iw / 44), 1));
    d.etiquetas.forEach(function (et, i) {
      if (i % cada === 0) svg.appendChild(el("text", { x: m.l + paso * i + paso / 2, y: H - 8, "text-anchor": "middle" }, et));
    });

    if (d.tipo === "barras") {
      var ns = d.series.length, ancho = Math.min((paso * 0.7) / ns, 38);
      d.series.forEach(function (s, si) {
        s.valores.forEach(function (v, i) {
          var h = (v / max) * ih;
          var x = m.l + paso * i + paso / 2 - (ancho * ns) / 2 + ancho * si;
          var r = el("rect", { x: x, y: m.t + ih - h, width: Math.max(ancho - 1, 1), height: Math.max(h, v > 0 ? 1.5 : 0), rx: 3, "class": "s-" + s.color });
          r.appendChild(el("title", {}, d.etiquetas[i] + ": " + (d.dinero ? "$" + miles(v) : v)));
          svg.appendChild(r);
        });
      });
    } else {
      d.series.forEach(function (s) {
        var pts = s.valores.map(function (v, i) { return [m.l + paso * i + paso / 2, m.t + ih - (v / max) * ih, v, i]; });
        svg.appendChild(el("path", { d: pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" "), "class": "s-" + s.color }));
        pts.forEach(function (p) {
          var c = el("circle", { cx: p[0], cy: p[1], r: 4.5, "class": "s-" + s.color });
          c.appendChild(el("title", {}, s.nombre + " (" + d.etiquetas[p[3]] + "): " + (d.dinero ? "$" + miles(p[2]) : p[2])));
          svg.appendChild(c);
        });
      });
    }
    cont.appendChild(svg);
  }

  function iniciar() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-grafico]"), function (cont) {
      var fuente = document.getElementById(cont.getAttribute("data-grafico"));
      if (!fuente) return;
      var datos;
      try { datos = JSON.parse(fuente.textContent); } catch (e) { return; }
      var pintar = function () { dibujar(cont, datos); };
      pintar();
      var t;
      window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(pintar, 120); });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar); else iniciar();
})();
