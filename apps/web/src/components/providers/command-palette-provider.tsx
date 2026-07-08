import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import { type LucideIcon, Search } from 'lucide-react';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { NAVIGATION } from '@/config/navigation';
import { useSearchSuggestions } from '@/hooks/use-search';
import { RESULT_TYPE_LABELS, type SearchResultType } from '@/types/search';

export interface Command {
  id: string;
  label: string;
  group: string;
  icon?: LucideIcon;
  keywords?: string[];
  run: () => void;
}

interface CommandPaletteContextValue {
  open: () => void;
  close: () => void;
  toggle: () => void;
  /** Register additional commands at runtime; returns an unregister fn. */
  register: (commands: Command[]) => () => void;
}

const CommandPaletteContext = React.createContext<CommandPaletteContextValue | null>(null);

/**
 * Command palette framework (⌘K / Ctrl+K). Navigation commands are seeded from
 * the nav config; features register their own commands via `register`.
 * When the user types 2+ characters, live suggestions from the search API appear.
 */
export function CommandPaletteProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = React.useState(false);
  const [dynamic, setDynamic] = React.useState<Command[]>([]);
  const [inputValue, setInputValue] = React.useState('');

  const open = React.useCallback(() => setIsOpen(true), []);
  const close = React.useCallback(() => {
    setIsOpen(false);
    setInputValue('');
  }, []);
  const toggle = React.useCallback(() => setIsOpen((v) => !v), []);

  const register = React.useCallback((commands: Command[]) => {
    setDynamic((prev) => [...prev, ...commands]);
    return () => {
      const ids = new Set(commands.map((c) => c.id));
      setDynamic((prev) => prev.filter((c) => !ids.has(c.id)));
    };
  }, []);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        toggle();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [toggle]);

  const navCommands = React.useMemo<Command[]>(
    () =>
      NAVIGATION.flatMap((group) =>
        group.items.map((item) => ({
          id: `nav:${item.key}`,
          label: `Go to ${item.label}`,
          group: 'Navigation',
          icon: item.icon,
          run: () => navigate(item.to),
        })),
      ),
    [navigate],
  );

  const allCommands = React.useMemo(() => [...navCommands, ...dynamic], [navCommands, dynamic]);
  const grouped = React.useMemo(() => {
    const map = new Map<string, Command[]>();
    for (const command of allCommands) {
      const list = map.get(command.group) ?? [];
      list.push(command);
      map.set(command.group, list);
    }
    return [...map.entries()];
  }, [allCommands]);

  // Live suggestions from search API
  const { data: suggestionsData } = useSearchSuggestions(inputValue, isOpen);
  const suggestions = suggestionsData?.suggestions ?? [];

  const value = React.useMemo(
    () => ({ open, close, toggle, register }),
    [open, close, toggle, register],
  );

  return (
    <CommandPaletteContext.Provider value={value}>
      {children}
      <CommandDialog open={isOpen} onOpenChange={(v) => { setIsOpen(v); if (!v) setInputValue(''); }}>
        <CommandInput
          placeholder="Search commands, cases, evidence…"
          value={inputValue}
          onValueChange={setInputValue}
        />
        <CommandList>
          <CommandEmpty>No matching commands or results.</CommandEmpty>

          {/* Live search suggestions */}
          {suggestions.length > 0 && (
            <>
              <CommandGroup heading="Suggestions">
                {suggestions.map((s, i) => (
                  <CommandItem
                    key={`suggestion:${i}`}
                    value={`suggestion:${s.text}`}
                    onSelect={() => {
                      close();
                      navigate(`/search?q=${encodeURIComponent(s.text)}`);
                    }}
                  >
                    <Search className="text-muted-foreground h-4 w-4" />
                    <span>{s.text}</span>
                    {s.suggestionType !== 'case' && (
                      <span className="ml-auto text-[11px] text-muted-foreground">
                        {RESULT_TYPE_LABELS[s.suggestionType as SearchResultType] ?? s.suggestionType}
                      </span>
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>

              {/* "Search for X" shortcut */}
              {inputValue.length >= 2 && (
                <CommandItem
                  value={`search-page:${inputValue}`}
                  onSelect={() => {
                    close();
                    navigate(`/search?q=${encodeURIComponent(inputValue)}`);
                  }}
                >
                  <Search className="text-muted-foreground h-4 w-4" />
                  Search for "{inputValue}" on search page
                </CommandItem>
              )}

              <CommandSeparator />
            </>
          )}

          {/* Navigation & registered commands */}
          {grouped.map(([groupName, commands]) => (
            <CommandGroup key={groupName} heading={groupName}>
              {commands.map((command) => {
                const Icon = command.icon;
                return (
                  <CommandItem
                    key={command.id}
                    value={`${command.label} ${command.keywords?.join(' ') ?? ''}`}
                    onSelect={() => {
                      command.run();
                      close();
                    }}
                  >
                    {Icon && <Icon className="text-muted-foreground" />}
                    {command.label}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          ))}
        </CommandList>
      </CommandDialog>
    </CommandPaletteContext.Provider>
  );
}

export function useCommandPalette(): CommandPaletteContextValue {
  const ctx = React.useContext(CommandPaletteContext);
  if (!ctx) throw new Error('useCommandPalette must be used within a CommandPaletteProvider');
  return ctx;
}
