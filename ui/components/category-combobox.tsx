"use client"

import { CheckIcon, ChevronsUpDownIcon, PlusIcon } from "lucide-react"
import * as React from "react"

import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import type { Category } from "@/lib/api"

interface CategoryComboboxProps {
  /** Label shown above the trigger button */
  label: string
  /** Currently selected category id, or null */
  value: string | null
  onChange: (categoryId: string | null) => void
  /** Available categories to search and select from */
  categories: Category[]
  /** Called when the user wants to create a new category with the given slug_segment */
  onCreateCategory?: (slug_segment: string) => Promise<void>
  /** Placeholder text shown when nothing is selected */
  placeholder?: string
  /** If true, the "Create" option is shown when no match is found */
  allowCreate?: boolean
  /** If true, the trigger is inert and cannot be opened */
  disabled?: boolean
  id?: string
}

export function CategoryCombobox({
  label,
  value,
  onChange,
  categories,
  onCreateCategory,
  placeholder = "Select category…",
  allowCreate = false,
  disabled = false,
  id,
}: CategoryComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const [creating, setCreating] = React.useState(false)

  const selected = categories.find((c) => c.id === value) ?? null

  const filtered = search
    ? categories.filter((c) => c.path.toLowerCase().includes(search.toLowerCase()))
    : categories

  const exactMatch = categories.some(
    (c) => c.slug_segment === search || c.path === search
  )

  async function handleCreate() {
    if (!onCreateCategory || !search.trim()) return
    setCreating(true)
    try {
      await onCreateCategory(search.trim())
      setSearch("")
      setOpen(false)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className="w-full justify-between font-normal"
          >
            <span className={cn("truncate", !selected && "text-muted-foreground")}>
              {selected ? selected.path : placeholder}
            </span>
            <ChevronsUpDownIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0">
          <Command>
            <CommandInput
              placeholder="Search or type slug…"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              <CommandEmpty>
                {allowCreate && search.trim() && !exactMatch ? (
                  <button
                    className="flex w-full items-center gap-2 px-2 py-1.5 text-sm hover:bg-accent"
                    onClick={handleCreate}
                    disabled={creating}
                  >
                    <PlusIcon className="h-4 w-4" />
                    {creating ? "Creating…" : `Create "${search.trim()}"`}
                  </button>
                ) : (
                  "No categories found."
                )}
              </CommandEmpty>
              <CommandGroup>
                {filtered.map((cat) => (
                  <CommandItem
                    key={cat.id}
                    value={cat.path}
                    onSelect={() => {
                      onChange(cat.id === value ? null : cat.id)
                      setSearch("")
                      setOpen(false)
                    }}
                  >
                    <CheckIcon
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === cat.id ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {cat.path}
                  </CommandItem>
                ))}
                {allowCreate && search.trim() && !exactMatch && filtered.length > 0 && (
                  <CommandItem
                    value={`__create__${search}`}
                    onSelect={handleCreate}
                    disabled={creating}
                  >
                    <PlusIcon className="mr-2 h-4 w-4" />
                    {creating ? "Creating…" : `Create "${search.trim()}"`}
                  </CommandItem>
                )}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  )
}
