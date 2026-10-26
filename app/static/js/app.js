/* Mi Cartera — comportamiento de la interfaz (sin librerías). */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // ---- Menú lateral (celular / tablet)
  var body = document.body;
  function setMenu(abierto) {
    body.classList.toggle("nav-open", abierto);
    $$("[data-abrir-menu]").forEach(function (b) { b.setAttribute("aria-expanded", abierto ? "true" : "false"); });
    if (abierto) { var c = $(".side__close"); if (c) c.focus(); }
  }
  $$("[data-abrir-menu]").forEach(function (b) { b.addEventListener("click", function () { setMenu(true); }); });
  $$("[data-cerrar-menu]").forEach(function (b) { b.addEventListener("click", function () { setMenu(false); }); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") setMenu(false); });

  // ---- Avisos que se pueden cerrar
  $$("[data-cerrar-aviso]").forEach(function (b) {
    b.addEventListener("click", function () { var a = b.closest(".flash"); if (a) a.remove(); });
  });

  // ---- Confirmaciones (data-confirmar="¿Seguro?") y evitar doble envío
  document.addEventListener("submit", function (e) {
    var f = e.target;
    var msg = f.getAttribute && f.getAttribute("data-confirmar");
    if (msg && !window.confirm(msg)) { e.preventDefault(); return; }
    // Un doble toque en el celular no debe registrar el cobro dos veces
    if (f.hasAttribute && f.hasAttribute("data-una-vez")) {
      if (f.dataset.enviado === "1") { e.preventDefault(); return; }
      f.dataset.enviado = "1";
      $$("button[type=submit]", f).forEach(function (b) { b.classList.add("is-busy"); });
    }
  });
  // Si se vuelve con "atrás", el formulario queda libre otra vez
  window.addEventListener("pageshow", function () {
    $$("form[data-una-vez]").forEach(function (f) {
      f.dataset.enviado = "0";
      $$("button.is-busy", f).forEach(function (b) { b.classList.remove("is-busy"); });
    });
  });

  // ---- Pesos con punto de miles mientras se escribe: 1234567 -> 1.234.567
  function formatoMiles(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, "."); }
  function soloDigitos(s) { return (s || "").replace(/\D/g, ""); }
  function pesos(n) { return "$" + formatoMiles(Math.round(n)); }
  $$("input[data-moneda]").forEach(function (inp) {
    function dar() {
      var d = soloDigitos(inp.value).replace(/^0+(?=\d)/, "");
      inp.value = d ? formatoMiles(d) : "";
    }
    inp.addEventListener("input", dar);
    dar();
  });

  // ---- Vista previa de un crédito: total, cuota y ganancia
  $$("[data-prestamo-form]").forEach(function (cont) {
    var v = $("[name=valor_inicial]", cont), i = $("[name=porcentaje_interes]", cont), c = $("[name=cantidad_cuotas]", cont);
    if (!v || !i || !c) return;
    function out(n, t) { var o = $("[data-out=" + n + "]", cont); if (o) o.textContent = t; }
    function calc() {
      var valor = parseFloat(soloDigitos(v.value)) || 0;
      var pct = parseFloat(String(i.value).replace(",", ".")) || 0;
      var cuotas = parseInt(c.value, 10) || 1;
      var total = valor + valor * pct / 100;
      out("total", pesos(total));
      out("cuota", pesos(total / Math.max(cuotas, 1)));
      out("ganancia", pesos(total - valor));
    }
    [v, i, c].forEach(function (el) { el.addEventListener("input", calc); });
    calc();
  });

  // ---- Botón "cobrar todo el saldo"
  $$("[data-llenar]").forEach(function (b) {
    b.addEventListener("click", function () {
      var dest = document.getElementById(b.getAttribute("data-llenar"));
      if (dest) { dest.value = formatoMiles(b.getAttribute("data-valor")); dest.focus(); }
    });
  });

  // ---- Reportes: mostrar solo los campos del tipo de período elegido
  var filtro = $("[data-filtro-periodo]");
  if (filtro) {
    var radios = $$("input[name=tipo]", filtro);
    var mostrar = function () {
      var sel = radios.filter(function (r) { return r.checked; })[0];
      $$("[data-panel]", filtro).forEach(function (p) {
        var visible = !!sel && p.getAttribute("data-panel").split(" ").indexOf(sel.value) >= 0;
        p.hidden = !visible;
        // Los campos ocultos no se envían (la URL queda limpia)
        $$("input, select", p).forEach(function (el) { el.disabled = !visible; });
      });
    };
    radios.forEach(function (r) { r.addEventListener("change", mostrar); });
    mostrar();
  }

  // ---- Enviar el formulario apenas cambia un selector automático
  $$("[data-autoenviar]").forEach(function (el) {
    el.addEventListener("change", function () { if (el.form) el.form.submit(); });
  });
})();
