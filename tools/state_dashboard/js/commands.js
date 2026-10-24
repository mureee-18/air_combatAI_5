function renderCmd(d) {
  let h = "";
  d.commands.forEach(group => {
    h += `<h2>${esc(group.group)}</h2>`;
    group.items.forEach(item => {
      h += `<div class="cmd"><span class="title">${esc(item.title)}</span>` +
           `<code>${esc(item.cmd)}</code>` +
           `<button data-cmd="${attr(item.cmd)}">コピー</button></div>`;
    });
  });
  document.getElementById("cmd").innerHTML = h;
  bindCopy(document.getElementById("cmd"));
}

function inlineCode(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/`(.+?)`/g, "<code>$1</code>");
}
