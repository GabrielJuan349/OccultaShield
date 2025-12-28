import { DOCUMENT } from '@angular/common';
import { Directive, ElementRef, inject, OnDestroy, OnInit, output, signal } from '@angular/core';

@Directive({
  selector: '[FileDrop]',
  host: {
    '[class.drag-over]': 'isDragOver()',
    '[class.drag-active-global]': 'isDragActiveGlobal()',
    '(dragover)': 'onDragOver($event)',
    '(dragleave)': 'onDragLeave($event)',
    '(drop)': 'onDrop($event)',
  },
})
export class FileDropDirective implements OnInit, OnDestroy {
  private readonly document = inject(DOCUMENT);
  private readonly elementRef = inject(ElementRef);

  /** Emite el archivo cuando el usuario lo suelta en la zona */
  readonly fileDropped = output<File>();

  /** Señal para controlar si el usuario está arrastrando algo encima de la zona */
  protected isDragOver = signal(false);

  /** Señal para indicar que hay un drag activo en cualquier parte del viewport */
  protected isDragActiveGlobal = signal(false);

  /** Contador para manejar eventos anidados de dragenter/dragleave */
  private dragCounter = 0;

  /** Referencias a los listeners para poder removerlos */
  private boundDragEnter = this.onDocumentDragEnter.bind(this);
  private boundDragOver = this.onDocumentDragOver.bind(this);
  private boundDragLeave = this.onDocumentDragLeave.bind(this);
  private boundDrop = this.onDocumentDrop.bind(this);

  ngOnInit(): void {
    // Capturar eventos de drag a nivel de documento
    this.document.addEventListener('dragenter', this.boundDragEnter);
    this.document.addEventListener('dragover', this.boundDragOver);
    this.document.addEventListener('dragleave', this.boundDragLeave);
    this.document.addEventListener('drop', this.boundDrop);
  }

  ngOnDestroy(): void {
    // Limpiar listeners al destruir la directiva
    this.document.removeEventListener('dragenter', this.boundDragEnter);
    this.document.removeEventListener('dragover', this.boundDragOver);
    this.document.removeEventListener('dragleave', this.boundDragLeave);
    this.document.removeEventListener('drop', this.boundDrop);
  }

  // ========== EVENTOS A NIVEL DE DOCUMENTO ==========

  private onDocumentDragEnter(evt: DragEvent): void {
    evt.preventDefault();
    this.dragCounter++;

    // Verificar si se están arrastrando archivos
    if (this.hasFiles(evt)) {
      this.isDragActiveGlobal.set(true);
    }
  }

  private onDocumentDragOver(evt: DragEvent): void {
    // Prevenir comportamiento por defecto (abrir archivo en el navegador)
    evt.preventDefault();

    // Cambiar el cursor para indicar que se puede soltar
    if (evt.dataTransfer && this.hasFiles(evt)) {
      evt.dataTransfer.dropEffect = 'copy';
    }
  }

  private onDocumentDragLeave(evt: DragEvent): void {
    evt.preventDefault();
    this.dragCounter--;

    // Solo desactivar cuando realmente salimos del viewport
    if (this.dragCounter <= 0) {
      this.dragCounter = 0;
      this.isDragActiveGlobal.set(false);
    }
  }

  private onDocumentDrop(evt: DragEvent): void {
    evt.preventDefault();
    evt.stopPropagation();

    // Resetear estado
    this.dragCounter = 0;
    this.isDragActiveGlobal.set(false);
    this.isDragOver.set(false);

    // Capturar el archivo sin importar dónde se soltó en la página
    const files = evt.dataTransfer?.files;
    if (files && files.length > 0 && this.hasFiles(evt)) {
      this.fileDropped.emit(files[0]);
    }
  }

  // ========== EVENTOS EN LA ZONA DE DROP ==========
  // (Estos manejan solo el estado visual cuando el cursor está sobre la zona)

  protected onDragOver(evt: DragEvent): void {
    evt.preventDefault();
    evt.stopPropagation();
    this.isDragOver.set(true);

    if (evt.dataTransfer) {
      evt.dataTransfer.dropEffect = 'copy';
    }
  }

  protected onDragLeave(evt: DragEvent): void {
    evt.preventDefault();
    evt.stopPropagation();
    this.isDragOver.set(false);
  }

  protected onDrop(evt: DragEvent): void {
    evt.preventDefault();
    evt.stopPropagation();
    this.isDragOver.set(false);

    const files = evt.dataTransfer?.files;
    if (files && files.length > 0) {
      this.fileDropped.emit(files[0]);
    }
  }

  // ========== HELPERS ==========

  private hasFiles(evt: DragEvent): boolean {
    if (!evt.dataTransfer) return false;

    // Verificar tipos de datos
    const types = evt.dataTransfer.types;
    return types.includes('Files') || types.includes('application/x-moz-file');
  }
}
