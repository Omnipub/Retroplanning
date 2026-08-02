/** Build local du CSS Tailwind, pour remplacer la CDN cdn.tailwindcss.com en
 * production (deconseillee par Tailwind lui-meme : elle charge tout le
 * compilateur JS a chaque page, cf. audit performance).
 *
 * A regenerer (npm run build:css) apres toute modification de classes
 * Tailwind dans templates/*.html, puis committer static/css/tailwind.css.
 */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#3F8078",
          alt: "#75A097",
        },
      },
    },
  },
  plugins: [],
};
