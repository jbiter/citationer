class Citationer < Formula
  desc "One-click bibliometric analysis CLI tool"
  homepage "https://github.com/jbiter/citationer"
  url "https://files.pythonhosted.org/packages/source/c/citationer/citationer-3.0.5.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"

  depends_on "python@3.11"

  resource "poetry" do
    url "https://files.pythonhosted.org/packages/source/p/poetry/poetry-1.7.1.tar.gz"
    sha256 "REPLACE_WITH_POETRY_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"citationer", "--version"
  end
end
