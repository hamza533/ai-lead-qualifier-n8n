import React from 'react';
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile } from 'remotion';
import { C } from './theme';
import { useInter } from './fonts';
import { BGM, CAPTIONS, FLASH_CUTS, SFX, SHOTS, TITLE_CARDS, TOTAL } from './timeline';
import { Caption } from './lib/Caption';
import { FlashCut } from './lib/FlashCut';
import { OrbitOpen } from './shots/OrbitOpen';
import { TitleCard } from './shots/TitleCard';
import { FormShot } from './shots/FormShot';
import { ResearchShot } from './shots/ResearchShot';
import { ScoreShot } from './shots/ScoreShot';
import { ApprovalShot } from './shots/ApprovalShot';
import { CrmShot } from './shots/CrmShot';
import { ResultsShot } from './shots/ResultsShot';
import { OutroShot } from './shots/OutroShot';

export type MainProps = { bgm: boolean };

const Shot: React.FC<{ id: keyof typeof SHOTS; children: React.ReactNode }> = ({ id, children }) => (
  <Sequence from={SHOTS[id].from} durationInFrames={SHOTS[id].duration} name={id}>
    {children}
  </Sequence>
);

export const Main: React.FC<MainProps> = ({ bgm }) => {
  useInter();
  return (
    <AbsoluteFill style={{ backgroundColor: C.surface }}>
      <Shot id="open">
        <OrbitOpen />
      </Shot>
      {(['tcArrive', 'tcHuman', 'tcReal'] as const).map((id) => (
        <Shot key={id} id={id}>
          <TitleCard {...TITLE_CARDS[id]} duration={SHOTS[id].duration} />
        </Shot>
      ))}
      <Shot id="form">
        <FormShot />
      </Shot>
      <Shot id="research">
        <ResearchShot />
      </Shot>
      <Shot id="score">
        <ScoreShot />
      </Shot>
      <Shot id="approval">
        <ApprovalShot />
      </Shot>
      <Shot id="crm">
        <CrmShot />
      </Shot>
      <Shot id="results">
        <ResultsShot />
      </Shot>
      <Shot id="outro">
        <OutroShot duration={SHOTS.outro.duration} />
      </Shot>

      {FLASH_CUTS.map((cut) => (
        <Sequence key={`flash-${cut}`} from={cut - 5} durationInFrames={10}>
          <FlashCut />
        </Sequence>
      ))}

      {CAPTIONS.map((c, i) => {
        const from = SHOTS[c.shot].from + c.at;
        const duration = (c.until ?? SHOTS[c.shot].duration - 2) - c.at;
        return (
          <Sequence key={`cap-${i}`} from={from} durationInFrames={duration}>
            <Caption main={c.main} sub={c.sub} duration={duration} />
          </Sequence>
        );
      })}

      {/* sound: one declarative table (timeline.ts), pinned relative to the shots */}
      {SFX.map((s, i) => (
        <Sequence key={`sfx-${i}`} from={s.from} durationInFrames={s.duration ?? 90} name={`sfx ${s.src}`}>
          <Audio src={staticFile(`audio/${s.src}`)} volume={s.volume} />
        </Sequence>
      ))}
      {bgm ? (
        <Audio
          src={staticFile(`audio/${BGM.src}`)}
          volume={(f) =>
            interpolate(f, [0, BGM.fadeIn, TOTAL - BGM.fadeOut, TOTAL], [0, BGM.volume, BGM.volume, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          }
        />
      ) : null}
    </AbsoluteFill>
  );
};
