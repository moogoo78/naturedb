$(document).ready(function () {
  $(document).scroll(function () {
    if ($(window).scrollTop() > 0) {
      $(".navbar").css({ "background-color": "black" });
    } else {
      $(".navbar").css({ "background-color": "transparent" });
    }
  });

  $(".photo-sildes").css({ width: window.innerWidth * 0.4 + "px" });
  $(".photo-sildes").slick({
    arrows: true,
    autoplay: false,
    slidesToShow: 1,
    slidesToScroll: 1,
  });
});
