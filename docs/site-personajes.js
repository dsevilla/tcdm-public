// Un personaje del cómic se posa en un elemento visible de la portada.
// La figura es decorativa y no participa en el flujo ni en los clics.
(() => {
  const nombres = ["duck", "flecha", "polar", "rusti"];
  const candidatos = document.querySelectorAll(
    ".sidebar-logo, .hero, main section:not(.hero)",
  );
  const visibles = [...candidatos].filter((elemento) => {
    const caja = elemento.getBoundingClientRect();
    // Sobre el borde de una tarjeta la figura asoma por encima: hace falta sitio.
    const cabe = elemento.matches(".hero, .sidebar-logo") ? caja.bottom > 0 : caja.top > 90;
    return caja.width >= 80 && caja.height >= 30
      && cabe && caja.top < window.innerHeight
      && caja.left < window.innerWidth && caja.right > 0;
  });
  if (visibles.length === 0) return;

  const anfitrion = visibles[Math.floor(Math.random() * visibles.length)];
  const nombre = nombres[Math.floor(Math.random() * nombres.length)];
  const personaje = document.createElement("img");
  personaje.src = `personajes/${nombre}.svg`;
  personaje.className = "personaje-flotante";
  personaje.alt = "";
  personaje.setAttribute("aria-hidden", "true");
  personaje.decoding = "async";
  personaje.addEventListener("error", () => personaje.remove(), { once: true });
  anfitrion.classList.add("personaje-anfitrion");
  anfitrion.append(personaje);
})();
