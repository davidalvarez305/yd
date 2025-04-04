const floatingHeader = document.getElementById("floatingHeader");
const scrollPercentageTrigger = 5;

function handleScroll() {
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const pageHeight =
    document.documentElement.scrollHeight -
    document.documentElement.clientHeight;

  const scrollPercentage = (scrollTop / pageHeight) * 100;

  if (scrollPercentage > scrollPercentageTrigger) {
    floatingHeader.style.display = "";
  } else {
    floatingHeader.style.display = "none";
  }
}

if (floatingHeader) window.addEventListener("scroll", handleScroll);