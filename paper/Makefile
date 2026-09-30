.PHONY: pdf clean figures verify

BUILD := build
MAIN  := manuscript

pdf:
	mkdir -p $(BUILD)
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -r latexmkrc; \
	else \
		echo "latexmk not found, falling back to manual pdflatex/biber sequence"; \
		pdflatex -interaction=nonstopmode -output-directory=$(BUILD) $(MAIN).tex; \
		biber --input-directory=$(BUILD) --output-directory=$(BUILD) $(MAIN); \
		pdflatex -interaction=nonstopmode -output-directory=$(BUILD) $(MAIN).tex; \
		pdflatex -interaction=nonstopmode -output-directory=$(BUILD) $(MAIN).tex; \
	fi
	cp $(BUILD)/$(MAIN).pdf ./$(MAIN).pdf

figures:
	python3 scripts/make_conceptual_diagram_check.py || true
	@echo "Figures are curated copies from the source model repository (see dev_mem/figure_manifest.md)."
	@echo "The one originally-authored figure (conceptual_framework) is built from scripts/conceptual_framework.tex:"
	cd scripts && pdflatex -interaction=nonstopmode conceptual_framework.tex >/dev/null
	cp scripts/conceptual_framework.pdf figures/main/conceptual_framework.pdf
	cd figures/main && pdftoppm -png -r 300 conceptual_framework.pdf conceptual_framework && mv conceptual_framework-1.png conceptual_framework.png

clean:
	rm -rf $(BUILD)
	rm -f $(MAIN).pdf
	rm -f scripts/*.aux scripts/*.log scripts/*.pdf scripts/conceptual_framework_preview*.png

verify: pdf
	python3 scripts/verify_manuscript.py
