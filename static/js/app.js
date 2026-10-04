document.addEventListener("DOMContentLoaded", () => {
  const typeField = document.querySelector("#id_movement_type");
  const dest = document.querySelector("#id_destination_warehouse");
  if (!typeField) return;

  const toggle = () => {
    const value = typeField.value;
    if (dest) dest.closest(".mb-3")?.classList.toggle("d-none", value !== "transfer");
  };
  typeField.addEventListener("change", toggle);
  toggle();
});
